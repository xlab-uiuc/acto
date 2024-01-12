"""The main engine of Acto. It is responsible for running the test cases and
collecting the results."""
import importlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from copy import deepcopy
from types import FunctionType

import deepdiff
import jsonpatch
import yaml

from acto.acto_config import ACTO_CONFIG
from acto.checker.checker_set import CheckerSet
from acto.common import (
    ErrorResult,
    OracleResult,
    PassResult,
    RecoveryResult,
    RunResult,
    kubernetes_client,
    print_event,
)
from acto.constant import CONST
from acto.deploy import Deploy
from acto.input import InputModel
from acto.input.input import OverSpecifiedField
from acto.input.known_schemas.base import K8sField
from acto.input.known_schemas.known_schema import find_all_matched_schemas_type
from acto.input.testcase import TestCase
from acto.input.testplan import TreeNode
from acto.input.value_with_schema import ValueWithSchema, attach_schema_to_value
from acto.input.valuegenerator import ArrayGenerator
from acto.kubectl_client import KubectlClient
from acto.kubernetes_engine import base, k3d, kind
from acto.lib.operator_config import OperatorConfig
from acto.oracle_handle import OracleHandle
from acto.runner import Runner
from acto.serialization import ActoEncoder, ContextEncoder
from acto.snapshot import Snapshot
from acto.utils import (
    delete_operator_pod,
    get_yaml_existing_namespace,
    process_crd,
    update_preload_images,
)
from acto.utils.thread_logger import get_thread_logger, set_thread_logger_prefix
from ssa.analysis import analyze

RECOVERY_SNAPSHOT = -2  # the immediate snapshot before the error


def save_result(
    trial_dir: str,
    trial_result: RunResult,
    num_tests: int,
    trial_elapsed,
    time_breakdown,
):
    """Save the result of a trial to a json file"""
    logger = get_thread_logger(with_prefix=False)

    result_dict = {}
    try:
        trial_num = "-".join(trial_dir.split("-")[-2:])
        result_dict["trial_num"] = trial_num
    except IndexError as _:
        result_dict["trial_num"] = trial_dir
    result_dict["duration"] = trial_elapsed
    result_dict["time_breakdown"] = time_breakdown
    result_dict["num_tests"] = num_tests
    if trial_result is None:
        logger.info("Trial %s completed without error", trial_dir)
    else:
        result_dict["error"] = trial_result.to_dict()
    result_path = os.path.join(trial_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as result_file:
        json.dump(result_dict, result_file, cls=ActoEncoder, indent=6)


def apply_testcase(
    value_with_schema: ValueWithSchema,
    path: list,
    testcase: TestCase,
    setup: bool = False,
) -> jsonpatch.JsonPatch:
    """Apply a testcase to a value"""
    logger = get_thread_logger(with_prefix=True)

    prev = value_with_schema.raw_value()
    field_curr_value = value_with_schema.get_value_by_path(list(path))
    if setup:
        value_with_schema.create_path(list(path))
        value_with_schema.set_value_by_path(
            testcase.setup(field_curr_value), list(path)
        )
        curr = value_with_schema.raw_value()
    else:
        if testcase.test_precondition(field_curr_value):
            value_with_schema.create_path(list(path))
            value_with_schema.set_value_by_path(
                testcase.mutator(field_curr_value), list(path)
            )
            curr = value_with_schema.raw_value()

    patch = jsonpatch.make_patch(prev, curr)
    logger.info("JSON patch: %s", patch)
    return patch


def check_state_equality(
    snapshot: Snapshot,
    prev_snapshot: Snapshot,
    additional_exclude_paths: list[str] = None,
) -> OracleResult:
    """Check whether two system state are semantically equivalent

    Args:
        - snapshot: a reference to a system state
        - prev_snapshot: a reference to another system state

    Return value:
        - a dict of diff results, empty if no diff found
    """
    logger = get_thread_logger(with_prefix=True)

    additional_exclude_paths = (
        additional_exclude_paths if additional_exclude_paths is not None else []
    )

    curr_system_state = deepcopy(snapshot.system_state)
    prev_system_state = deepcopy(prev_snapshot.system_state)

    if len(curr_system_state) == 0 or len(prev_system_state) == 0:
        return PassResult()

    del curr_system_state["endpoints"]
    del prev_system_state["endpoints"]
    del curr_system_state["job"]
    del prev_system_state["job"]

    # remove pods that belong to jobs from both states to avoid observability problem
    curr_pods = curr_system_state["pod"]
    prev_pods = prev_system_state["pod"]
    curr_system_state["pod"] = {
        k: v
        for k, v in curr_pods.items()
        if v["metadata"]["owner_references"][0]["kind"] != "Job"
    }
    prev_system_state["pod"] = {
        k: v
        for k, v in prev_pods.items()
        if v["metadata"]["owner_references"][0]["kind"] != "Job"
    }

    for _, obj in prev_system_state["secret"].items():
        if "data" in obj and obj["data"] is not None:
            for key, data in obj["data"].items():
                try:
                    obj["data"][key] = json.loads(data)
                except json.JSONDecodeError as _:
                    pass

    for _, obj in curr_system_state["secret"].items():
        if "data" in obj and obj["data"] is not None:
            for key, data in obj["data"].items():
                try:
                    obj["data"][key] = json.loads(data)
                except json.JSONDecodeError as _:
                    pass

    # remove custom resource from both states
    curr_system_state.pop("custom_resource_spec", None)
    prev_system_state.pop("custom_resource_spec", None)
    curr_system_state.pop("custom_resource_status", None)
    prev_system_state.pop("custom_resource_status", None)
    curr_system_state.pop("pvc", None)
    prev_system_state.pop("pvc", None)

    # remove fields that are not deterministic
    exclude_paths = [
        r".*\['metadata'\]\['managed_fields'\]",
        r".*\['metadata'\]\['cluster_name'\]",
        r".*\['metadata'\]\['creation_timestamp'\]",
        r".*\['metadata'\]\['resource_version'\]",
        r".*\['metadata'\].*\['uid'\]",
        r".*\['metadata'\]\['generation'\]$",
        r".*\['metadata'\]\['annotations'\]",
        r".*\['metadata'\]\['annotations'\]\['.*last-applied.*'\]",
        r".*\['metadata'\]\['annotations'\]\['.*\.kubernetes\.io.*'\]",
        r".*\['metadata'\]\['labels'\]\['.*revision.*'\]",
        r".*\['metadata'\]\['labels'\]\['owner-rv'\]",
        r".*\['status'\]",
        r"\['metadata'\]\['deletion_grace_period_seconds'\]",
        r"\['metadata'\]\['deletion_timestamp'\]",
        r".*\['spec'\]\['init_containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['volumes'\]\[.*\]\['name'\]$",
        r".*\[.*\]\['node_name'\]$",
        r".*\[\'spec\'\]\[\'host_users\'\]$",
        r".*\[\'spec\'\]\[\'os\'\]$",
        r".*\[\'grpc\'\]$",
        r".*\[\'spec\'\]\[\'volume_name\'\]$",
        r".*\['version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['uid'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['resource_version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['ip'\]",
        r".*\['cluster_ip'\]$",
        r".*\['cluster_i_ps'\].*$",
        r".*\['deployment_pods'\].*\['metadata'\]\['name'\]$",
        r".*\['daemonset_pods'\].*\['metadata'\]\['name'\]$",
        r"\[\'config_map\'\]\[\'kube\-root\-ca\.crt\'\]\[\'data\'\]\[\'ca\.crt\'\]$",
        r".*\['secret'\].*$",
        r"\['secrets'\]\[.*\]\['name'\]",
        r".*\['node_port'\]",
        r".*\['metadata'\]\['generate_name'\]",
        r".*\['metadata'\]\['labels'\]\['pod\-template\-hash'\]",
        r"\['deployment_pods'\].*\['metadata'\]\['owner_references'\]\[.*\]\['name'\]",
    ]

    exclude_paths.extend(additional_exclude_paths)

    diff = deepdiff.DeepDiff(
        prev_system_state,
        curr_system_state,
        exclude_regex_paths=exclude_paths,
        view="tree",
    )

    if diff:
        logger.debug(
            "failed attempt recovering to seed state - system state diff: %s",
            diff,
        )
        return RecoveryResult(
            delta=diff, from_=prev_system_state, to_=curr_system_state
        )

    return PassResult()


class TrialRunner:
    """Test driver of Acto. One TrialRunner is one worker for Acto, and each
    TrialRunner is independant.
    """

    def __init__(
        self,
        context: dict,
        input_model: InputModel,
        deploy: Deploy,
        runner_t: type,
        checker_t: type,
        wait_time: int,
        custom_on_init: list[callable],
        custom_oracle: list[callable],
        workdir: str,
        cluster: base.KubernetesEngine,
        worker_id: int,
        sequence_base: int,
        dryrun: bool,
        is_reproduce: bool,
        apply_testcase_f: FunctionType,
        acto_namespace: int,
        additional_exclude_paths: list[str] = None,
    ) -> None:
        self.context = context
        self.workdir = workdir
        self.base_workdir = workdir
        self.cluster = cluster
        self.images_archive = os.path.join(workdir, "images.tar")
        self.worker_id = worker_id
        self.sequence_base = sequence_base  # trial number to start with
        self.context_name = cluster.get_context_name(
            f"acto-{acto_namespace}-cluster-{worker_id}"
        )
        self.kubeconfig = os.path.join(
            os.path.expanduser("~"), ".kube", self.context_name
        )
        self.cluster_name = f"acto-{acto_namespace}-cluster-{worker_id}"
        self.input_model = input_model
        self.deploy = deploy
        self.runner_t = runner_t
        self.checker_t = checker_t
        self.wait_time = wait_time  # seconds of the resettable timer
        self.additional_exclude_paths = (
            additional_exclude_paths
            if additional_exclude_paths is not None
            else []
        )

        self.custom_on_init = custom_on_init
        self.custom_oracle = custom_oracle
        self.dryrun = dryrun
        self.is_reproduce = is_reproduce

        self.snapshots = []
        self.discarded_testcases = {}  # List of test cases failed to run
        self.apply_testcase_f = apply_testcase_f

        self.curr_trial = 0

    def run(self, errors: list[RunResult], mode: str = InputModel.NORMAL):
        """Start running the test cases"""
        logger = get_thread_logger(with_prefix=True)

        self.input_model.set_worker_id(self.worker_id)
        apiclient = None

        self.input_model.set_mode(mode)
        if mode != InputModel.NORMAL:
            self.workdir = os.path.join(self.workdir, mode)
            os.makedirs(self.base_workdir, exist_ok=True)

        while True:
            if self.input_model.is_empty():
                logger.info("Test finished")
                break

            trial_start_time = time.time()
            self.cluster.restart_cluster(self.cluster_name, self.kubeconfig)
            apiclient = kubernetes_client(self.kubeconfig, self.context_name)
            self.cluster.load_images(self.images_archive, self.cluster_name)
            trial_k8s_bootstrap_time = time.time()
            kubectl_client = KubectlClient(self.kubeconfig, self.context_name)
            deployed = self.deploy.deploy_with_retry(
                self.kubeconfig,
                self.context_name,
                kubectl_client=kubectl_client,
                namespace=self.context["namespace"],
            )
            if not deployed:
                logger.info("Not deployed. Try again!")
                continue
            operator_deploy_time = time.time()
            trial_dir = os.path.join(
                self.workdir,
                f"trial-{self.worker_id + self.sequence_base:02d}-{self.curr_trial:04d}",
            )
            os.makedirs(trial_dir, exist_ok=True)

            trial_err, num_tests = self.run_trial(
                trial_dir=trial_dir, curr_trial=self.curr_trial
            )
            self.snapshots = []

            trial_finished_time = time.time()
            trial_elapsed = time.strftime(
                "%H:%M:%S", time.gmtime(trial_finished_time - trial_start_time)
            )
            logger.info(
                "Trial %d finished, completed in %s",
                self.curr_trial,
                trial_elapsed,
            )
            logger.info(
                "Kubernetes bootstrap: %d",
                trial_k8s_bootstrap_time - trial_start_time,
            )
            logger.info(
                "Operator deploy: %d",
                operator_deploy_time - trial_k8s_bootstrap_time,
            )
            logger.info(
                "Trial run: %d", trial_finished_time - operator_deploy_time
            )
            logger.info("---------------------------------------\n")

            delete_operator_pod(apiclient, self.context["namespace"])
            save_result(
                trial_dir,
                trial_err,
                num_tests,
                trial_elapsed,
                {
                    "k8s_bootstrap": trial_k8s_bootstrap_time
                    - trial_start_time,
                    "operator_deploy": operator_deploy_time
                    - trial_k8s_bootstrap_time,
                    "trial_run": trial_finished_time - operator_deploy_time,
                },
            )
            self.curr_trial = self.curr_trial + 1
            errors.append(trial_err)

            if self.input_model.is_empty():
                logger.info("Test finished")
                break

        logger.info(
            "Failed test cases: %s",
            json.dumps(self.discarded_testcases, cls=ActoEncoder, indent=4),
        )

    def run_trial(
        self, trial_dir: str, curr_trial: int, num_mutation: int = 10
    ) -> tuple[ErrorResult, int]:
        """Run a trial starting with the initial input, mutate with the candidate_dict,
        and mutate for num_mutation times

        Args:
            initial_input: the initial input without mutation
            candidate_dict: guides the mutation
            trial_num: how many trials have been run
            num_mutation: how many mutations to run at each trial
        """
        oracle_handle = OracleHandle(
            KubectlClient(self.kubeconfig, self.context_name),
            kubernetes_client(self.kubeconfig, self.context_name),
            self.context["namespace"],
            self.snapshots,
        )
        # first run the on_init callbacks if any
        if self.custom_on_init is not None:
            for on_init in self.custom_on_init:
                on_init(oracle_handle)

        runner: Runner = self.runner_t(
            self.context,
            trial_dir,
            self.kubeconfig,
            self.context_name,
            wait_time=self.wait_time,
            operator_container_name=self.deploy.operator_container_name
        )
        checker: CheckerSet = self.checker_t(
            self.context,
            trial_dir,
            self.input_model,
            oracle_handle,
            self.custom_oracle,
        )

        curr_input = self.input_model.get_seed_input()
        self.snapshots.append(Snapshot(curr_input))

        generation = 0
        while (
            generation < num_mutation
        ):  # every iteration gets a new list of next tests
            # update the thread logger
            set_thread_logger_prefix(f"trial: {curr_trial}, gen: {generation}")
            logger = get_thread_logger(with_prefix=True)

            curr_input_with_schema = attach_schema_to_value(
                self.snapshots[-1].input, self.input_model.root_schema
            )

            ready_testcases = []
            if generation > 0:
                if self.input_model.is_empty():
                    break
                test_groups = self.input_model.next_test()

                # if test_group is None, it means this group is exhausted
                # break and move to the next trial
                if test_groups is None:
                    break

                # First make sure all the next tests are valid
                for (
                    group,
                    testcase_with_path,
                ) in test_groups:  # iterate on list of next tests
                    field_path_str, testcase = testcase_with_path
                    field_path = json.loads(field_path_str)
                    testcase_signature = {
                        "field": field_path_str,
                        "testcase": str(testcase),
                    }
                    field_curr_value = curr_input_with_schema.get_value_by_path(
                        list(field_path)
                    )

                    if testcase.test_precondition(field_curr_value):
                        # precondition of this testcase satisfies
                        logger.info("Precondition of %s satisfies", field_path)
                        ready_testcases.append((group, testcase_with_path))
                    else:
                        # precondition fails, first run setup
                        logger.info(
                            "Precondition of %s fails, try setup first",
                            field_path_str,
                        )

                        self.apply_testcase_f(
                            curr_input_with_schema,
                            field_path,
                            testcase,
                            setup=True,
                        )

                        if not testcase.test_precondition(
                            curr_input_with_schema.get_value_by_path(
                                list(field_path)
                            )
                        ):
                            # just in case the setup does not work correctly, drop this testcase
                            logger.error("Setup does not work correctly")
                            group.discard_testcase(self.discarded_testcases)
                            continue

                        run_result = TrialRunner.run_and_check(
                            runner=runner,
                            checker=checker,
                            input_cr=curr_input_with_schema.raw_value(),
                            snapshots=self.snapshots,
                            generation=generation,
                            testcase_signature=testcase_signature,
                        )
                        generation += 1

                        if run_result.is_connection_refused():
                            logger.error("Connection refused, exiting")
                            return run_result, generation

                        is_invalid, _ = run_result.is_invalid()
                        if run_result.is_basic_error():
                            group.discard_testcase(self.discarded_testcases)
                            # before return, run the recovery test case
                            run_result.recovery_result = self.run_recovery(
                                runner
                            )
                            generation += 1

                            return run_result, generation
                        elif is_invalid:
                            logger.info("Setup produced invalid input")
                            self.snapshots.pop()
                            group.discard_testcase(self.discarded_testcases)
                            curr_input_with_schema = self.revert(
                                runner, checker, generation
                            )
                            generation += 1
                        elif run_result.is_unchanged():
                            logger.info("Setup produced unchanged input")
                            group.discard_testcase(self.discarded_testcases)
                        elif run_result.is_error():
                            group.discard_testcase(self.discarded_testcases)
                            # before return, run the recovery test case
                            run_result.recovery_result = self.run_recovery(
                                runner
                            )
                            generation += 1

                            return run_result, generation
                        else:
                            ready_testcases.append((group, testcase_with_path))

                if len(ready_testcases) == 0:
                    logger.info("All setups failed")
                    continue
                logger.info("Running bundled testcases")

            t = self.run_testcases(
                curr_input_with_schema,
                ready_testcases,
                runner,
                checker,
                generation,
            )
            run_result, generation = t
            is_invalid, _ = run_result.is_invalid()
            if (
                not is_invalid and run_result.is_error()
            ) or run_result.is_basic_error():
                # before return, run the recovery test case

                logger.info("Error result, running recovery")
                run_result.recovery_result = self.run_recovery(runner)
                generation += 1

                return run_result, generation

            if self.input_model.is_empty():
                logger.info("Input model is empty, break")
                break

        return None, generation

    def run_testcases(
        self,
        curr_input_with_schema,
        testcases: list[tuple[TreeNode, TestCase]],
        runner,
        checker,
        generation,
    ) -> tuple[RunResult, int]:
        """Run a list of testcases on the current input"""
        logger = get_thread_logger(with_prefix=True)

        testcase_patches = []
        testcase_signature = None
        for group, testcase_with_path in testcases:
            field_path_str, testcase = testcase_with_path
            field_path = json.loads(field_path_str)
            testcase_signature = {
                "field": field_path_str,
                "testcase": str(testcase),
            }
            patch = self.apply_testcase_f(
                curr_input_with_schema, field_path, testcase
            )

            # field_node.get_testcases().pop()  # finish testcase
            testcase_patches.append((group, testcase_with_path, patch))

        run_result = TrialRunner.run_and_check(
            runner=runner,
            checker=checker,
            input_cr=curr_input_with_schema.raw_value(),
            snapshots=self.snapshots,
            generation=generation,
            testcase_signature=testcase_signature,
        )
        generation += 1
        if run_result.is_connection_refused():
            logger.error("Connection refused, exiting")
            return run_result, generation

        is_invalid, invalid_result = run_result.is_invalid()
        if is_invalid:
            # If the result indicates our input is invalid, we need to first run revert to
            # go back to previous system state, then construct a new input without the
            # responsible testcase and re-apply

            # 1. revert
            logger.debug("Invalid input, revert")
            self.snapshots.pop()
            curr_input_with_schema = self.revert(runner, checker, generation)
            generation += 1

            # 2. Construct a new input and re-apply
            if len(testcase_patches) == 1:
                # if only one testcase, then no need to isolate
                testcase_patches[0][0].finish_testcase()  # finish testcase
                logger.debug("Only one patch, no need to isolate")
                return run_result, generation
            else:
                responsible_field = invalid_result.responsible_field
                if responsible_field is None:
                    # Unable to pinpoint the exact responsible testcase, try one by one
                    logger.debug(
                        "Unable to pinpoint the exact responsible field, try one by one"
                    )
                    for group, testcase_with_path, patch in testcase_patches:
                        iso_result, generation = self.run_testcases(
                            curr_input_with_schema,
                            [(group, testcase_with_path)],
                            runner,
                            checker,
                            generation,
                        )
                        if (
                            not iso_result.is_invalid()[0]
                            and iso_result.is_error()
                        ) or iso_result.is_basic_error():
                            return iso_result, generation
                    return run_result, generation
                else:
                    jsonpatch_path = "".join(
                        "/" + str(item) for item in responsible_field
                    )
                    logger.debug("Responsible patch path: %s", jsonpatch_path)
                    # isolate the responsible invalid testcase and re-apply
                    ready_testcases = []
                    for group, testcase_with_path, patch in testcase_patches:
                        responsible = False
                        for op in patch:
                            if op["path"] == jsonpatch_path:
                                logger.info(
                                    "Determine the responsible field to be %s",
                                    jsonpatch_path,
                                )
                                responsible = True
                                group.finish_testcase()  # finish testcase
                                break
                        if not responsible:
                            ready_testcases.append((group, testcase_with_path))
                    if len(ready_testcases) == 0:
                        return run_result, generation

                    if len(ready_testcases) == len(testcase_patches):
                        logger.error(
                            "Fail to determine the responsible patch, try one by one"
                        )
                        for (
                            group,
                            testcase_with_path,
                            patch,
                        ) in testcase_patches:
                            iso_result, generation = self.run_testcases(
                                curr_input_with_schema,
                                [(group, testcase_with_path)],
                                runner,
                                checker,
                                generation,
                            )
                            if (
                                not iso_result.is_invalid()[0]
                                and iso_result.is_error()
                            ) or iso_result.is_basic_error():
                                return iso_result, generation
                        return run_result, generation
                    else:
                        logger.debug("Rerunning the remaining ready testcases")
                        return self.run_testcases(
                            curr_input_with_schema,
                            ready_testcases,
                            runner,
                            checker,
                            generation,
                        )
        else:
            if not self.is_reproduce:
                for patch in testcase_patches:
                    patch[0].finish_testcase()  # finish testcase
            return run_result, generation

    @staticmethod
    def run_and_check(
        runner: Runner,
        checker: CheckerSet,
        input_cr: dict,
        snapshots: list,
        generation: int,
        testcase_signature: dict,
        revert: bool = False,
    ) -> RunResult:
        """Run the test case and use oracles to check the result"""
        logger = get_thread_logger(with_prefix=True)
        logger.debug("Run and check")

        retry = 0
        while True:
            snapshot, _ = runner.run(input_cr, generation)
            run_result = checker.check(
                snapshot,
                snapshots[-1],
                revert,
                generation,
                testcase_signature=testcase_signature,
            )
            snapshots.append(snapshot)

            if run_result.is_connection_refused():
                # Connection refused due to webhook not ready, let's wait for a bit
                logger.info(
                    "Connection failed. Retry the test after 60 seconds"
                )
                time.sleep(60)
                retry += 1

                if retry > 2:
                    logger.error("Connection failed too many times. Abort")
                    break
            else:
                break

        return run_result

    def run_recovery(self, runner: Runner) -> OracleResult:
        """Runs the recovery test case after an error is reported"""
        logger = get_thread_logger(with_prefix=True)

        logger.debug("Running recovery")
        recovery_input = self.snapshots[RECOVERY_SNAPSHOT].input
        snapshot, _ = runner.run(recovery_input, generation=-1)
        result = check_state_equality(
            snapshot,
            self.snapshots[RECOVERY_SNAPSHOT],
            self.additional_exclude_paths,
        )

        return result

    def revert(self, runner, checker, generation) -> ValueWithSchema:
        """Revert to the previous system state"""
        curr_input_with_schema = attach_schema_to_value(
            self.snapshots[-1].input, self.input_model.root_schema
        )

        testcase_sig = {"field": "", "testcase": "revert"}

        _ = TrialRunner.run_and_check(
            runner=runner,
            checker=checker,
            input_cr=curr_input_with_schema.raw_value(),
            snapshots=self.snapshots,
            generation=generation,
            testcase_signature=testcase_sig,
            revert=True,
        )
        return curr_input_with_schema


class Acto:
    """The main class of Acto."""

    def __init__(
        self,
        workdir_path: str,
        operator_config: OperatorConfig,
        cluster_runtime: str,
        preload_images_: list,
        context_file: str,
        helper_crd: str,
        num_workers: int,
        num_cases: int,
        dryrun: bool,
        analysis_only: bool,
        is_reproduce: bool,
        input_model: type,
        apply_testcase_f: FunctionType,
        reproduce_dir: str = None,
        delta_from: str = None,
        mount: list = None,
        focus_fields: list = None,
        acto_namespace: int = 0,
    ) -> None:
        logger = get_thread_logger(with_prefix=False)

        try:
            with open(
                operator_config.seed_custom_resource, "r", encoding="utf-8"
            ) as cr_file:
                self.seed = yaml.load(cr_file, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            logger.error("Failed to read seed yaml, aborting: %s", e)
            sys.exit(1)

        deploy = Deploy(operator_config.deploy)

        if cluster_runtime == "KIND":
            cluster = kind.Kind(
                acto_namespace=acto_namespace,
                feature_gates=operator_config.kubernetes_engine.feature_gates,
            )
        elif cluster_runtime == "K3D":
            cluster = k3d.K3D()
        else:
            logger.warning(
                "Cluster Runtime %s is not supported, defaulted to use kind",
                cluster_runtime,
            )
            cluster = kind.Kind(
                acto_namespace=acto_namespace,
                feature_gates=operator_config.kubernetes_engine.feature_gates,
            )

        self.cluster = cluster
        self.deploy = deploy
        self.operator_config = operator_config
        self.crd_name = operator_config.crd_name
        self.workdir_path = workdir_path
        self.images_archive = os.path.join(workdir_path, "images.tar")
        self.num_workers = num_workers
        self.dryrun = dryrun
        self.is_reproduce = is_reproduce
        self.apply_testcase_f = apply_testcase_f
        self.reproduce_dir = reproduce_dir
        self.acto_namespace = acto_namespace

        self.runner_type = Runner
        self.checker_type = CheckerSet
        self.snapshots = []

        # generate configuration files for the cluster runtime
        self.cluster.configure_cluster(
            operator_config.num_nodes, self.operator_config.kubernetes_version
        )

        self.__learn(
            context_file=context_file,
            helper_crd=helper_crd,
            analysis_only=analysis_only,
        )

        # Add additional preload images from arguments
        if preload_images_ is not None:
            self.context["preload_images"].update(preload_images_)

        # Apply custom fields
        if operator_config.analysis is not None:
            used_fields = self.context["analysis_result"]["used_fields"]
        else:
            used_fields = None
        self.input_model: InputModel = input_model(
            self.context["crd"]["body"],
            used_fields,
            operator_config.example_dir,
            num_workers,
            num_cases,
            self.reproduce_dir,
            mount,
        )
        self.input_model.initialize(self.seed)

        applied_custom_k8s_fields = False

        if operator_config.k8s_fields is not None:
            module = importlib.import_module(operator_config.k8s_fields)
            if hasattr(module, "BLACKBOX") and ACTO_CONFIG.mode == "blackbox":
                applied_custom_k8s_fields = True
                for k8s_field in module.BLACKBOX:
                    self.input_model.apply_k8s_schema(k8s_field)
            elif hasattr(module, "WHITEBOX") and ACTO_CONFIG.mode == "whitebox":
                applied_custom_k8s_fields = True
                for k8s_field in module.WHITEBOX:
                    self.input_model.apply_k8s_schema(k8s_field)
        if not applied_custom_k8s_fields:
            # default to use the known_schema module to automatically find the mapping
            # from CRD to K8s schema
            logger.info(
                "Using known_schema to find the mapping from CRD to K8s schema"
            )
            tuples = find_all_matched_schemas_type(self.input_model.root_schema)
            for match_tuple in tuples:
                logger.debug(
                    "Found matched schema: %s -> %s",
                    match_tuple[0].path,
                    match_tuple[1],
                )
                k8s_schema = K8sField(match_tuple[0].path, match_tuple[1])
                self.input_model.apply_k8s_schema(k8s_schema)

        if operator_config.custom_fields is not None:
            if ACTO_CONFIG.mode == "blackbox":
                pruned_list = []
                module = importlib.import_module(operator_config.custom_fields)
                for custom_field in module.custom_fields:
                    pruned_list.append(custom_field.path)
                    self.input_model.apply_custom_field(custom_field)
            else:
                pruned_list = []
                module = importlib.import_module(operator_config.custom_fields)
                for custom_field in module.custom_fields:
                    pruned_list.append(custom_field.path)
                    self.input_model.apply_custom_field(custom_field)
        else:
            pruned_list = []
            tuples = find_all_matched_schemas_type(self.input_model.root_schema)
            for match_tuple in tuples:
                custom_field = OverSpecifiedField(
                    match_tuple[0].path,
                    array=isinstance(match_tuple[1], ArrayGenerator),
                )
                self.input_model.apply_custom_field(custom_field)

        self.sequence_base = 20 if delta_from else 0

        if operator_config.custom_oracle is not None:
            module = importlib.import_module(operator_config.custom_oracle)
            self.custom_oracle = module.CUSTOM_CHECKER
            self.custom_on_init = module.ON_INIT
        else:
            self.custom_oracle = None
            self.custom_on_init = None

        # Generate test cases
        testplan_path = None
        if delta_from is not None:
            testplan_path = os.path.join(delta_from, "test_plan.json")
        self.test_plan = self.input_model.generate_test_plan(
            testplan_path, focus_fields=focus_fields
        )
        with open(
            os.path.join(self.workdir_path, "test_plan.json"),
            "w",
            encoding="utf-8",
        ) as plan_file:
            json.dump(self.test_plan, plan_file, cls=ActoEncoder, indent=4)

    def __learn(self, context_file, helper_crd, analysis_only=False):
        logger = get_thread_logger(with_prefix=False)

        learn_start_time = time.time()

        if os.path.exists(context_file):
            logger.info("Loading context from file")
            with open(context_file, "r", encoding="utf-8") as context_fin:
                self.context = json.load(context_fin)
                self.context["preload_images"] = set(
                    self.context["preload_images"]
                )

            if analysis_only and self.operator_config.analysis is not None:
                logger.info("Only run learning analysis")
                with tempfile.TemporaryDirectory() as project_src:
                    subprocess.run(
                        args=[
                            "git",
                            "clone",
                            self.operator_config.analysis.github_link,
                            project_src,
                        ],
                        check=True,
                    )
                    subprocess.run(
                        args=[
                            "git",
                            "-C",
                            project_src,
                            "checkout",
                            self.operator_config.analysis.commit,
                        ],
                        check=True,
                    )

                    if self.operator_config.analysis.entrypoint is not None:
                        entrypoint_path = os.path.join(
                            project_src,
                            self.operator_config.analysis.entrypoint,
                        )
                    else:
                        entrypoint_path = project_src
                    self.context["analysis_result"] = analyze(
                        entrypoint_path,
                        self.operator_config.analysis.type,
                        self.operator_config.analysis.package,
                    )

                learn_end_time = time.time()
                self.context["static_analysis_time"] = (
                    learn_end_time - learn_start_time
                )

                with open(context_file, "w", encoding="utf-8") as context_fout:
                    json.dump(
                        self.context,
                        context_fout,
                        cls=ContextEncoder,
                        indent=4,
                        sort_keys=True,
                    )
        else:
            # Run learning run to collect some information from runtime
            logger.info("Starting learning run to collect information")
            self.context = {
                "namespace": "",
                "crd": None,
                "preload_images": set(),
            }
            learn_context_name = self.cluster.get_context_name("learn")
            learn_kubeconfig = os.path.join(
                os.path.expanduser("~"), ".kube", learn_context_name
            )

            while True:
                self.cluster.restart_cluster("learn", learn_kubeconfig)
                namespace = (
                    get_yaml_existing_namespace(self.deploy.operator_yaml)
                    or CONST.ACTO_NAMESPACE
                )
                self.context["namespace"] = namespace
                kubectl_client = KubectlClient(
                    learn_kubeconfig, learn_context_name
                )
                deployed = self.deploy.deploy_with_retry(
                    learn_kubeconfig,
                    learn_context_name,
                    kubectl_client=kubectl_client,
                    namespace=namespace,
                )
                if deployed:
                    break
            apiclient = kubernetes_client(learn_kubeconfig, learn_context_name)
            runner = Runner(
                self.context, "learn", learn_kubeconfig, learn_context_name, self.deploy.operator_container_name
            )
            runner.run_without_collect(
                self.operator_config.seed_custom_resource
            )

            update_preload_images(
                self.context, self.cluster.get_node_list("learn")
            )
            self.context["crd"] = process_crd(
                apiclient,
                KubectlClient(learn_kubeconfig, learn_context_name),
                self.crd_name,
                helper_crd,
            )
            self.cluster.delete_cluster("learn", learn_kubeconfig)

            run_end_time = time.time()

            if self.operator_config.analysis is not None:
                with tempfile.TemporaryDirectory() as project_src:
                    subprocess.run(
                        args=[
                            "git",
                            "clone",
                            self.operator_config.analysis.github_link,
                            project_src,
                        ],
                        check=True,
                    )
                    subprocess.run(
                        args=[
                            "git",
                            "-C",
                            project_src,
                            "checkout",
                            self.operator_config.analysis.commit,
                        ],
                        check=True,
                    )

                    if self.operator_config.analysis.entrypoint is not None:
                        entrypoint_path = os.path.join(
                            project_src,
                            self.operator_config.analysis.entrypoint,
                        )
                    else:
                        entrypoint_path = project_src
                    self.context["analysis_result"] = analyze(
                        entrypoint_path,
                        self.operator_config.analysis.type,
                        self.operator_config.analysis.package,
                    )

            learn_end_time = time.time()

            self.context["static_analysis_time"] = learn_end_time - run_end_time
            self.context["learnrun_time"] = run_end_time - learn_start_time
            with open(context_file, "w", encoding="utf-8") as context_fout:
                json.dump(
                    self.context,
                    context_fout,
                    cls=ContextEncoder,
                    indent=4,
                    sort_keys=True,
                )

    def run(
        self, modes: list = ["normal", "overspecified", "copiedover"]
    ) -> list[RunResult]:
        """Run the test cases"""
        logger = get_thread_logger(with_prefix=True)

        # Build an archive to be preloaded
        if len(self.context["preload_images"]) > 0:
            logger.info("Creating preload images archive")
            print_event("Preparing required images...")
            # first make sure images are present locally
            for image in self.context["preload_images"]:
                subprocess.run(
                    ["docker", "pull", image],
                    stdout=subprocess.DEVNULL,
                    check=True,
                )
            subprocess.run(
                ["docker", "image", "save", "-o", self.images_archive]
                + list(self.context["preload_images"]),
                stdout=subprocess.DEVNULL,
                check=True,
            )

        start_time = time.time()

        errors: list[RunResult] = []
        runners: list[TrialRunner] = []
        for i in range(self.num_workers):
            runner = TrialRunner(
                self.context,
                self.input_model,
                self.deploy,
                self.runner_type,
                self.checker_type,
                self.operator_config.wait_time,
                self.custom_on_init,
                self.custom_oracle,
                self.workdir_path,
                self.cluster,
                i,
                self.sequence_base,
                self.dryrun,
                self.is_reproduce,
                self.apply_testcase_f,
                self.acto_namespace,
                self.operator_config.diff_ignore_fields
            )
            runners.append(runner)

        if "normal" in modes:
            threads = []
            for runner in runners:
                t = threading.Thread(target=runner.run, args=[errors])
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        normal_time = time.time()

        if "overspecified" in modes:
            threads = []
            for runner in runners:
                t = threading.Thread(
                    target=runner.run, args=([errors, InputModel.OVERSPECIFIED])
                )
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        overspecified_time = time.time()

        if "copiedover" in modes:
            threads = []
            for runner in runners:
                t = threading.Thread(
                    target=runner.run, args=([errors, InputModel.COPIED_OVER])
                )
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        additional_semantic_time = time.time()

        if InputModel.ADDITIONAL_SEMANTIC in modes:
            threads = []
            for runner in runners:
                t = threading.Thread(
                    target=runner.run,
                    args=([errors, InputModel.ADDITIONAL_SEMANTIC]),
                )
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        end_time = time.time()

        num_total_failed = 0
        for runner in runners:
            for testcases in runner.discarded_testcases.values():
                num_total_failed += len(testcases)

        testrun_info = {
            "normal_duration": normal_time - start_time,
            "overspecified_duration": overspecified_time - normal_time,
            "copied_over_duration": additional_semantic_time
            - overspecified_time,
            "additional_semantic_duration": end_time - additional_semantic_time,
            "num_workers": self.num_workers,
            "num_total_testcases": self.input_model.metadata,
            "num_total_failed": num_total_failed,
        }
        with open(
            os.path.join(self.workdir_path, "testrun_info.json"),
            "w",
            encoding="utf-8",
        ) as info_file:
            json.dump(testrun_info, info_file, cls=ActoEncoder, indent=4)

        logger.info("All tests finished")
        return errors
