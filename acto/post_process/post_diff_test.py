import argparse
import difflib
import glob
import hashlib
import itertools
import json
import logging
import multiprocessing
import multiprocessing.queues
import os
import queue
import re
import subprocess
import sys
import threading
import time
from copy import deepcopy
from typing import Optional

import pandas as pd
import pydantic
import yaml
from deepdiff import DeepDiff
from deepdiff.helper import CannotCompare
from deepdiff.model import DiffLevel, TreeResult
from deepdiff.operator import BaseOperator

from acto.checker.impl.health import HealthChecker
from acto.common import invalid_input_message_regex, kubernetes_client
from acto.deploy import Deploy
from acto.kubectl_client.kubectl import KubectlClient
from acto.kubernetes_engine import base, kind
from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_process import PostProcessor
from acto.result import (
    CliStatus,
    DifferentialOracleResult,
    OracleResult,
    StepID,
)
from acto.runner import Runner
from acto.serialization import ActoEncoder
from acto.snapshot import Snapshot
from acto.trial import Step
from acto.utils import add_acto_label, error_handler, get_thread_logger


class DiffTestResult(pydantic.BaseModel):
    """The result of a diff test
    It contains the input digest, the snapshot, the original trial and generation,
        and the time spent on each step
        The oracle result is separated from this dataclass,
        so that it can easily recomputed after changing the oracle
    """

    input_digest: str
    snapshot: Snapshot
    originals: list[dict]
    time: dict

    @classmethod
    def from_file(cls, file_path: str) -> "DiffTestResult":
        """Initializes a DiffTestResult from a file"""
        with open(file_path, "r", encoding="utf-8") as f:
            diff_test_result = json.load(f)
        return cls(
            input_digest=diff_test_result["input_digest"],
            snapshot=diff_test_result["snapshot"],
            originals=diff_test_result["originals"],
            time=diff_test_result["time"],
        )

    def to_file(self, file_path: str):
        """Dump the DiffTestResult to a file"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, cls=ActoEncoder, indent=4)


def dict_hash(d: dict) -> int:
    """Hash a dict"""
    return hash(json.dumps(d, sort_keys=True))


def compare_system_equality(
    curr_system_state: dict,
    prev_system_state: dict,
    additional_exclude_paths: Optional[list[str]] = None,
) -> Optional[dict]:
    """Compare two system states and return the diff if they are not equal, otherwise return None"""
    logger = get_thread_logger(with_prefix=False)
    curr_system_state = deepcopy(curr_system_state)
    prev_system_state = deepcopy(prev_system_state)

    try:
        del curr_system_state["endpoints"]
        del prev_system_state["endpoints"]
        del curr_system_state["job"]
        del prev_system_state["job"]
    except KeyError:
        return None

    # remove pods that belong to jobs from both states to avoid observability problem
    curr_pods = curr_system_state["pod"]
    prev_pods = prev_system_state["pod"]

    new_pods = {}
    for k, v in curr_pods.items():
        if (
            "metadata" in v
            and "owner_references" in v["metadata"]
            and v["metadata"]["owner_references"] is not None
            and v["metadata"]["owner_references"][0]["kind"] != "Job"
        ):
            new_pods[k] = v
    curr_system_state["pod"] = new_pods

    new_pods = {}
    for k, v in prev_pods.items():
        if (
            "metadata" in v
            and "owner_references" in v["metadata"]
            and v["metadata"]["owner_references"] is not None
            and v["metadata"]["owner_references"][0]["kind"] != "Job"
        ):
            new_pods[k] = v
    prev_system_state["pod"] = new_pods

    for _, obj in prev_system_state["secret"].items():
        if "data" in obj and obj["data"] is not None:
            for key, data in obj["data"].items():
                try:
                    obj["data"][key] = json.loads(data)
                except json.JSONDecodeError:
                    pass

    for _, obj in curr_system_state["secret"].items():
        if "data" in obj and obj["data"] is not None:
            for key, data in obj["data"].items():
                try:
                    obj["data"][key] = json.loads(data)
                except json.JSONDecodeError:
                    pass

    if len(curr_system_state["secret"]) != len(prev_system_state["secret"]):
        logger.debug(
            "failed attempt recovering to seed state - secret count mismatch"
        )
        return DeepDiff(
            {"secret_number": len(prev_system_state["secret"])},
            {"secret_number": len(curr_system_state["secret"])},
            view="tree",
        )

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
        r".*\['metadata'\]\['annotations'\]\['.*last-applied.*'\]",
        r".*\['metadata'\]\['annotations'\]\['.*\.kubernetes\.io.*'\]",
        r".*\['metadata'\]\['labels'\]\['.*revision.*'\]",
        r".*\['metadata'\]\['labels'\]\['owner-rv'\]",
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
        r"\[\'config_map\'\]\[\'kube\-root\-ca\.crt\'\]\[\'data\'\]\[\'ca\.crt\'\]$",
        r".*\['secret'\].*$",
        r"\['secrets'\]\[.*\]\['name'\]",
        r".*\['node_port'\]",
        r".*\['metadata'\]\['generate_name'\]",
        r".*\['metadata'\]\['labels'\]\['pod\-template\-hash'\]",
        r"\['deployment_pods'\].*\['metadata'\]\['owner_references'\]\[.*\]\['name'\]",
        r"\['status'\]\['conditions'\]\[.*\]\['last_transition_time'\]",
        r".*\['container_id'\]",
        r".*\['started_at'\]",
        r".*\['finished_at'\]",
        r".*\['host_ip'\]",
        r".*\['status'\]\['host_ip'\]",
        r".*\['status'\]\['host_i_ps'\]\[.*\]\['ip'\]",
        r".*\['status'\]\['pod_ip'\]",
        r".*\['status'\]\['pod_i_ps'\]\[.*\]\['ip'\]",
        r".*\['status'\]\['start_time'\]",
        r".*\['status'\]\['observed_generation'\]",
        r".*\['last_transition_time'\]",
        r".*\['last_update_time'\]",
        r".*\['image_id'\]",
        r".*\['restart_count'\]",
        r".*\['status'\]\['container_statuses'\]\[.*\]\['last_state'\]",
        r".*\['status'\]\['current_replicas'\]",
        r".*\['status'\]\['current_revision'\]",
        r".*\['status'\]\['update_revision'\]",
    ]

    if additional_exclude_paths is not None:
        exclude_paths.extend(additional_exclude_paths)

    for e in exclude_paths:
        re.compile(e)

    diff = DeepDiff(
        prev_system_state,
        curr_system_state,
        exclude_regex_paths=exclude_paths,
        iterable_compare_func=compare_func,
        ignore_order=True,
        custom_operators=[
            NameOperator(r".*\['name'\]$"),
            TypeChangeOperator(r".*\['annotations'\]$"),
        ],
        view="tree",
    )

    postprocess_deepdiff(diff)

    if diff:
        logger.debug(
            "failed attempt recovering to seed state - system state diff: %s",
            diff,
        )
        return diff

    return None


def postprocess_deepdiff(diff: TreeResult):
    """Postprocess the deepdiff result to ignore non-deterministic fields"""
    # ignore PVC add/removal, because PVC can be intentially left behind
    logger = get_thread_logger(with_prefix=False)
    if "dictionary_item_removed" in diff:
        new_removed_items = []
        for removed_item in diff["dictionary_item_removed"]:
            if removed_item.path(output_format="list")[0] == "pvc":
                logger.debug("ignoring removed pvc %s", removed_item)
            else:
                new_removed_items.append(removed_item)
        if len(new_removed_items) == 0:
            del diff["dictionary_item_removed"]
        else:
            diff["dictionary_item_removed"] = new_removed_items

    if "dictionary_item_added" in diff:
        new_removed_items = []
        for removed_item in diff["dictionary_item_added"]:
            if removed_item.path(output_format="list")[0] == "pvc":
                logger.debug("ignoring added pvc %s", removed_item)
            else:
                new_removed_items.append(removed_item)
        if len(new_removed_items) == 0:
            del diff["dictionary_item_added"]
        else:
            diff["dictionary_item_added"] = new_removed_items


def compare_func(x, y, _: DiffLevel = None):
    """Compare function for deepdiff taking key and operator into account"""
    try:
        if "name" in x and "name" in y:
            # Take name into account, e.g., PVCs, volumes
            x_name = x["name"]
            y_name = y["name"]
            if len(x_name) < 5 or len(y_name) < 5:
                return x_name == y_name
            return x_name[:5] == y_name[:5]
        if "key" in (x, y) and "operator" in (x, y):
            return x["key"] == y["key"] and x["operator"] == y["operator"]
        if "type" in (x, y):
            # Compare the Pod conditions
            return x["type"] == y["type"]
    except:
        raise CannotCompare() from None
    raise CannotCompare() from None


class NameOperator(BaseOperator):
    """Operator to compare the object taking into consideration of the name field"""

    def give_up_diffing(self, level, diff_instance):
        _ = diff_instance
        x_name = level.t1
        y_name = level.t2
        if x_name is None or y_name is None:
            return False
        if re.search(r"^.+-([A-Za-z0-9]{5})$", x_name) and re.search(
            r"^.+-([A-Za-z0-9]{5})$", y_name
        ):
            return x_name[:5] == y_name[:5]
        return False


class TypeChangeOperator(BaseOperator):
    """Operator to compare the object taking into consideration of the type change"""

    def give_up_diffing(self, level, diff_instance):
        if level.t1 is None:
            if isinstance(level.t2, dict):
                level.t1 = {}
            elif isinstance(level.t2, list):
                level.t1 = []
        elif level.t2 is None:
            if isinstance(level.t1, dict):
                logging.info("t2 is None, t1 is dict")
                level.t2 = {}
            elif isinstance(level.t1, list):
                level.t2 = []
        return False


def get_nondeterministic_fields(s1, s2, additional_exclude_paths):
    """Get the nondeterministic fields between two system states"""
    nondeterministic_fields = []
    result = compare_system_equality(
        s1, s2, additional_exclude_paths=additional_exclude_paths
    )
    if result is not None:
        diff = result
        for diff_type, diffs in diff.items():
            if diff_type == "dictionary_item_removed":
                for diff_field in diffs:
                    nondeterministic_fields.append(
                        diff_field.path(output_format="list")
                    )
            elif diff_type == "dictionary_item_added":
                for diff_field in diffs:
                    nondeterministic_fields.append(
                        diff_field.path(output_format="list")
                    )
            elif diff_type == "values_changed":
                for diff_field in diffs:
                    nondeterministic_fields.append(
                        diff_field.path(output_format="list")
                    )
            elif diff_type == "type_changes":
                for diff_field in diffs:
                    nondeterministic_fields.append(
                        diff_field.path(output_format="list")
                    )
    return nondeterministic_fields


class AdditionalRunner:
    """Additional Runner"""

    def __init__(
        self,
        context: dict,
        deploy: Deploy,
        workdir: str,
        cluster: base.KubernetesEngine,
        worker_id,
        acto_namespace: int,
    ):
        self._context = context
        self._deploy = deploy
        self._workdir = workdir
        self._cluster = cluster
        self._worker_id = worker_id
        self._cluster_name = f"acto-{acto_namespace}-cluster-{worker_id}"
        self._context_name = cluster.get_context_name(
            f"acto-{acto_namespace}-cluster-{worker_id}"
        )
        self._kubeconfig = os.path.join(
            os.path.expanduser("~"), ".kube", self._context_name
        )
        self._generation = 0
        self._images_archive = os.path.join(workdir, "images.tar")

    def run_cr(self, cr, trial, gen):
        """Run a CR and return the snapshot"""
        self._cluster.restart_cluster(self._cluster_name, self._kubeconfig)
        self._cluster.load_images(self._images_archive, self._cluster_name)
        apiclient = kubernetes_client(self._kubeconfig, self._context_name)
        kubectl_client = KubectlClient(self._kubeconfig, self._context_name)
        _ = self._deploy.deploy_with_retry(
            self._kubeconfig,
            self._context_name,
            kubectl_client=kubectl_client,
            namespace=self._context["namespace"],
        )
        add_acto_label(apiclient, self._context["namespace"])
        trial_dir = os.path.join(self._workdir, f"trial-{self._worker_id:02d}")
        os.makedirs(trial_dir, exist_ok=True)
        runner = Runner(
            self._context,
            trial_dir,
            self._kubeconfig,
            self._context_name,
            operator_container_name=self._deploy.operator_container_name,
        )
        snapshot, _ = runner.run(cr, generation=self._generation)
        snapshot.dump(runner.trial_dir)
        difftest_result = {
            "input_digest": hashlib.md5(
                json.dumps(cr, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "snapshot": snapshot.to_dict(),
            "originals": {
                "trial": trial,
                "gen": gen,
            },
        }
        difftest_result_path = os.path.join(
            trial_dir, f"difftest-{self._generation:03d}.json"
        )
        with open(difftest_result_path, "w", encoding="utf-8") as f:
            json.dump(difftest_result, f, cls=ActoEncoder, indent=6)

        return snapshot


class DeployRunner:
    """Deploy runner for Acto"""

    def __init__(
        self,
        workqueue: multiprocessing.Queue,
        context: dict,
        deploy: Deploy,
        workdir: str,
        cluster: base.KubernetesEngine,
        worker_id,
        acto_namespace: int,
    ):
        self._workqueue = workqueue
        self._context = context
        self._deploy = deploy
        self._workdir = workdir
        self._cluster = cluster
        self._worker_id = worker_id
        self._cluster_name = f"acto-{acto_namespace}-cluster-{worker_id}"
        self._context_name = cluster.get_context_name(
            f"acto-{acto_namespace}-cluster-{worker_id}"
        )
        self._kubeconfig = os.path.join(
            os.path.expanduser("~"), ".kube", self._context_name
        )
        self._images_archive = os.path.join(workdir, "images.tar")

    def run(self):
        """Run the deploy runner"""
        logger = get_thread_logger(with_prefix=True)
        generation = 0
        trial_dir = os.path.join(self._workdir, f"trial-{self._worker_id:02d}")
        os.makedirs(trial_dir, exist_ok=True)

        before_k8s_bootstrap_time = time.time()
        # Start the cluster and deploy the operator
        self._cluster.restart_cluster(self._cluster_name, self._kubeconfig)
        self._cluster.load_images(self._images_archive, self._cluster_name)
        kubectl_client = KubectlClient(self._kubeconfig, self._context_name)
        after_k8s_bootstrap_time = time.time()
        _ = self._deploy.deploy_with_retry(
            self._kubeconfig,
            self._context_name,
            kubectl_client=kubectl_client,
            namespace=self._context["namespace"],
        )
        after_operator_deploy_time = time.time()

        trial_dir = os.path.join(self._workdir, f"trial-{self._worker_id:02d}")
        os.makedirs(trial_dir, exist_ok=True)
        runner = Runner(
            self._context,
            trial_dir,
            self._kubeconfig,
            self._context_name,
            operator_container_name=self._deploy.operator_container_name,
        )
        while True:
            after_k8s_bootstrap_time = time.time()
            try:
                group = self._workqueue.get(block=True, timeout=5)
            except queue.Empty:
                break

            cr = group.iloc[0]["input"]

            snapshot, err = runner.run(cr, generation=generation)
            snapshot.dump(runner.trial_dir)
            after_run_time = time.time()
            err = True
            difftest_result = DiffTestResult(
                input_digest=group.iloc[0]["input_digest"],
                snapshot=snapshot,
                originals=group[["trial", "gen"]].to_dict("records"),
                time={
                    "k8s_bootstrap": after_k8s_bootstrap_time
                    - before_k8s_bootstrap_time,
                    "operator_deploy": after_operator_deploy_time
                    - after_k8s_bootstrap_time,
                    "run": after_run_time - after_operator_deploy_time,
                },
            )
            difftest_result_path = os.path.join(
                trial_dir, f"difftest-{generation:03d}.json"
            )
            difftest_result.to_file(difftest_result_path)

            if err:
                before_k8s_bootstrap_time = time.time()
                logger.error("Restart cluster due to error: %s", err)
                # Start the cluster and deploy the operator
                self._cluster.restart_cluster(
                    self._cluster_name, self._kubeconfig
                )
                self._cluster.load_images(
                    self._images_archive, self._cluster_name
                )
                kubectl_client = KubectlClient(
                    self._kubeconfig, self._context_name
                )
                after_k8s_bootstrap_time = time.time()
                _ = self._deploy.deploy_with_retry(
                    self._kubeconfig,
                    self._context_name,
                    kubectl_client=kubectl_client,
                    namespace=self._context["namespace"],
                )
                after_operator_deploy_time = time.time()
                runner = Runner(
                    self._context,
                    trial_dir,
                    self._kubeconfig,
                    self._context_name,
                    operator_container_name=self._deploy.operator_container_name,
                )

            generation += 1


def compute_common_regex(paths: list[str]) -> list[str]:
    """Compute the common regex from the list of paths"""
    common_regex: set[str] = set()
    sorted_paths = sorted(paths)
    curr_regex = None
    for i in range(len(sorted_paths)):
        if curr_regex is None or not re.match(curr_regex, sorted_paths[i]):
            # if we do not have enough items to look ahead, then we give up
            if i + 2 >= len(sorted_paths):
                common_regex.add("^" + re.escape(sorted_paths[i]) + "$")
                continue

            path = sorted_paths[i]
            next_path = sorted_paths[i + 1]
            next_next_path = sorted_paths[i + 2]

            # if the resource type is different, then we give up to avoid
            # a wildcard regex
            if (
                path.startswith("root")
                and next_path.startswith("root")
                and next_next_path.startswith("root")
            ):
                resource_type = re.findall(r"root\['(.*?)'\]", path)[0]
                next_resource_type = re.findall(r"root\['(.*?)'\]", next_path)[
                    0
                ]
                next_next_resource_type = re.findall(
                    r"root\['(.*?)'\]", next_next_path
                )[0]
                if (
                    resource_type != next_resource_type
                    or next_resource_type != next_next_resource_type
                ):
                    common_regex.add("^" + re.escape(path) + "$")
                    continue

            # Look ahead to find a regex candidate
            # Construct the regex candidate using the difflib
            matched_blocks = difflib.SequenceMatcher(
                None,
                path,
                next_path,
            ).get_matching_blocks()
            regex_candidate = r""
            for block in matched_blocks:
                if block.a == 0 and block.b == 0:
                    regex_candidate += r"^"
                elif block.size != 0:
                    # we may have duplicate wild card here,
                    # but it is fine because two consequence wild cards is
                    # equivalent to one wild card
                    regex_candidate += r".*"

                if block.size <= 3:
                    # prevent accidental single character match in random string
                    continue
                regex_candidate += re.escape(
                    path[block.a : block.a + block.size]
                )
            regex_candidate += r"$"

            # Check if the regex candidate is valid for the third item
            # if matched, then we have a valid regex
            # if not, then we give up finding a common regex for the current
            # item
            if re.match(regex_candidate, next_next_path):
                common_regex.add(regex_candidate)
                curr_regex = regex_candidate
            else:
                common_regex.add("^" + re.escape(path) + "$")
    return list(common_regex)


class PostDiffTest(PostProcessor):
    """Post diff test class for Acto"""

    def __init__(
        self,
        testrun_dir: str,
        config: OperatorConfig,
        ignore_invalid: bool = False,
        acto_namespace: int = 0,
    ):
        self.acto_namespace = acto_namespace
        super().__init__(testrun_dir, config)
        logger = get_thread_logger(with_prefix=True)

        self.all_inputs = []
        for trial_name, trial in self.trial_to_steps.items():
            for step in trial.steps.values():
                if step.run_result.cli_status == CliStatus.INVALID:
                    # If the input is rejected by the operator webhook,
                    # we still run it, but the oracle only checks the explicit
                    # error state
                    pass
                else:
                    invalid = step.run_result.is_invalid_input()
                    if invalid and not ignore_invalid:
                        continue
                self.all_inputs.append(
                    {
                        "trial": trial_name,
                        "gen": step.run_result.step_id.generation,
                        "input": step.snapshot.input_cr,
                        "input_digest": hashlib.md5(
                            json.dumps(
                                step.snapshot.input_cr, sort_keys=True
                            ).encode("utf-8")
                        ).hexdigest(),
                        "operator_log": step.snapshot.operator_log,
                        "system_state": step.snapshot.system_state,
                        "cli_output": step.snapshot.cli_result,
                    }
                )

        self.df = pd.DataFrame(
            self.all_inputs,
            columns=[
                "trial",
                "gen",
                "input",
                "input_digest",
                "operator_log",
                "system_state",
                "cli_output",
            ],
        )

        # input digest -> group of steps
        self.unique_inputs: dict[str, pd.DataFrame] = {}
        groups = self.df.groupby("input_digest")
        for digest, group in groups:
            self.unique_inputs[digest] = group

        logger.info("Found %d unique inputs", len(self.unique_inputs))
        print(groups.count())
        series = groups.count().sort_values("trial", ascending=False)
        print(series.head())

    def post_process(self, workdir: str, num_workers: int = 1):
        """Start the post process"""
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        cluster = kind.Kind(
            acto_namespace=self.acto_namespace,
            feature_gates=self.config.kubernetes_engine.feature_gates,
            num_nodes=self.config.num_nodes,
            version=self.config.kubernetes_version,
        )
        deploy = Deploy(self.config.deploy)
        # Build an archive to be preloaded
        images_archive = os.path.join(workdir, "images.tar")
        if len(self.context["preload_images"]) > 0:
            # first make sure images are present locally
            for image in self.context["preload_images"]:
                subprocess.run(["docker", "pull", image], check=True)
            subprocess.run(
                ["docker", "image", "save", "-o", images_archive]
                + list(self.context["preload_images"]),
                check=True,
            )

        workqueue: multiprocessing.Queue = multiprocessing.Queue()
        for unique_input_group in self.unique_inputs.values():
            workqueue.put(unique_input_group)

        runners: list[DeployRunner] = []
        for i in range(num_workers):
            runner = DeployRunner(
                workqueue,
                self.context,
                deploy,
                workdir,
                cluster,
                i,
                self.acto_namespace,
            )
            runners.append(runner)

        processes = []
        for runner in runners:
            p = multiprocessing.Process(target=runner.run)
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    def check(self, workdir: str, num_workers: int = 1):
        """Check the post process result"""
        logger = get_thread_logger(with_prefix=True)
        trial_dirs = glob.glob(os.path.join(workdir, "trial-*"))

        with open(self.config.seed_custom_resource, "r", encoding="utf-8") as f:
            seed_cr = yaml.load(f, Loader=yaml.FullLoader)
            seed_input_digest = hashlib.md5(
                json.dumps(seed_cr, sort_keys=True).encode("utf-8")
            ).hexdigest()

        workqueue: multiprocessing.Queue = multiprocessing.Queue()
        for trial_dir in trial_dirs:
            for diff_test_result_path in glob.glob(
                os.path.join(trial_dir, "difftest-*.json")
            ):
                # 1. Populate the workqueue
                workqueue.put(diff_test_result_path)

                # 2. Find the seed test result and compute the common regex
                diff_test_result = DiffTestResult.from_file(
                    diff_test_result_path
                )
                if diff_test_result.input_digest == seed_input_digest:
                    diff_skip_regex = self.__get_diff_paths(
                        diff_test_result, num_workers
                    )
                    logger.info(
                        "Seed input digest: %s, diff_skip_regex: %s",
                        seed_input_digest,
                        diff_skip_regex,
                    )
                    if self.config.diff_ignore_fields is None:
                        self.config.diff_ignore_fields = diff_skip_regex
                    else:
                        self.config.diff_ignore_fields.extend(diff_skip_regex)

        logger.info(
            "Additional exclude paths: %s", self.config.diff_ignore_fields
        )

        processes = []
        for i in range(num_workers):
            p = multiprocessing.Process(
                target=self.check_diff_test_result, args=(workqueue, workdir, i)
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    def check_diff_test_result(
        self, workqueue: multiprocessing.Queue, workdir: str, worker_id: int
    ):
        """Check the diff test result"""
        additional_runner_dir = os.path.join(
            workdir, f"additional-runner-{worker_id}"
        )
        cluster = kind.Kind(
            acto_namespace=self.acto_namespace,
            feature_gates=self.config.kubernetes_engine.feature_gates,
            num_nodes=self.config.num_nodes,
            version=self.config.kubernetes_version,
        )

        deploy = Deploy(self.config.deploy)

        runner = AdditionalRunner(
            context=self.context,
            deploy=deploy,
            workdir=additional_runner_dir,
            cluster=cluster,
            worker_id=worker_id,
            acto_namespace=self.acto_namespace,
        )

        while True:
            try:
                diff_test_result_path = workqueue.get(block=True, timeout=5)
            except queue.Empty:
                break

            diff_test_result = DiffTestResult.from_file(diff_test_result_path)
            originals = diff_test_result.originals

            group_errs = []
            for original in originals:
                trial = original["trial"]
                gen = original["gen"]

                if gen == 0:
                    continue

                trial_basename = os.path.basename(trial)
                original_result = self.trial_to_steps[trial_basename].steps[
                    str(gen)
                ]
                step_result = PostDiffTest.check_diff_test_step(
                    diff_test_result,
                    original_result,
                    self.config,
                    False,
                    runner,
                )
                if step_result is None:
                    continue
                group_errs.append(step_result)
            if len(group_errs) > 0:
                with open(
                    os.path.join(
                        workdir,
                        f"compare-results-{diff_test_result.input_digest}.json",
                    ),
                    "w",
                    encoding="utf-8",
                ) as result_f:
                    json.dump(group_errs, result_f, cls=ActoEncoder, indent=4)

    @staticmethod
    def check_diff_test_step(
        diff_test_result: DiffTestResult,
        original_result: Step,
        config: OperatorConfig,
        run_check_indeterministic: bool = False,
        additional_runner: Optional[AdditionalRunner] = None,
    ) -> Optional[OracleResult]:
        """Check the diff test step result and return the differential oracle "
        "result if it fails, otherwise return None"""
        logger = get_thread_logger(with_prefix=True)
        trial_dir = original_result.run_result.step_id.trial
        gen = original_result.run_result.step_id.generation

        if original_result.run_result.oracle_result.health is not None:
            return None

        if diff_test_result.snapshot.cli_result["stderr"]:
            # Input is considered as invalid by the APIServer
            # Do not run oracle on this input
            return None

        if original_result.run_result.cli_status == CliStatus.INVALID:
            # we run the system health oracle here only,
            # without running the differential oracle
            return HealthChecker().check(snapshot=diff_test_result.snapshot)

        original_operator_log = original_result.snapshot.operator_log
        if invalid_input_message_regex(original_operator_log):
            return None

        original_system_state = original_result.snapshot.system_state
        result = compare_system_equality(
            diff_test_result.snapshot.system_state,
            original_system_state,
            config.diff_ignore_fields,
        )
        if not result:
            logger.info("Pass diff test for trial %s gen %d", trial_dir, gen)
            return None
        elif run_check_indeterministic:
            if additional_runner is None:
                raise ValueError(
                    "additional_runner must be provided if run_check_indeterministic is True"
                )
            add_snapshot = additional_runner.run_cr(
                diff_test_result.snapshot.input_cr, trial_dir, gen
            )
            indeterministic_fields = get_nondeterministic_fields(
                original_system_state,
                add_snapshot.system_state,
                config.diff_ignore_fields,
            )

            if len(indeterministic_fields) > 0:
                logger.info(
                    "Got additional nondeterministic fields: %s",
                    indeterministic_fields,
                )
                for delta_category in result:
                    for delta in result[delta_category]:
                        if (
                            delta.path(output_format="list")
                            not in indeterministic_fields
                        ):
                            logger.error(
                                "Fail diff test for trial %s gen %d",
                                trial_dir,
                                gen,
                            )
                            return DifferentialOracleResult(
                                message="failed attempt recovering to seed state "
                                "- system state diff",
                                diff=result,
                                from_step=StepID(
                                    trial=trial_dir, generation=gen
                                ),
                                from_state=original_system_state,
                                to_step=StepID(
                                    trial=diff_test_result.input_digest,
                                    generation=0,
                                ),
                                to_state=diff_test_result.snapshot.system_state,
                            )
                return None
            else:
                logger.error(
                    "Fail diff test for trial %s gen %d", trial_dir, gen
                )
                return DifferentialOracleResult(
                    message="failed attempt recovering to seed state - system state diff",
                    diff=result,
                    from_step=StepID(trial=trial_dir, generation=gen),
                    from_state=original_system_state,
                    to_step=StepID(
                        trial=diff_test_result.input_digest, generation=0
                    ),
                    to_state=diff_test_result.snapshot.system_state,
                )
        else:
            logger.error("Fail diff test for trial %s gen %d", trial_dir, gen)
            return DifferentialOracleResult(
                message="failed attempt recovering to seed state - system state diff",
                diff=result,
                from_step=StepID(trial=trial_dir, generation=gen),
                from_state=original_system_state,
                to_step=StepID(
                    trial=diff_test_result.input_digest, generation=0
                ),
                to_state=diff_test_result.snapshot.system_state,
            )

    def __get_diff_paths(
        self, diff_test_result: DiffTestResult, num_workers: int
    ) -> list[str]:
        """Get the diff paths from a diff test result
        Algorithm:
            Iterate on the original trials, in principle they should be the same
            If they are not, the diffs should be the indeterministic fields
            to be skipped when doing the comparison.
            Naively, we can just append all the indeterministic fields and return
            them, however, there are cases where the field path itself is not
            deterministic (e.g. the name of the secret could be randomly generated)
            To handle this randomness in the name, we can use the first two
            original trials to compare the system state to get the initial
            regex for skipping.
            If we do not have random names, the subsequent trials should not
            have additional indeterministic fields.

            Then, we keep iterating on the rest of the original results, and
            check if we have additional indeterministic fields. If we do, we
            collect them and try to figure out the proper regex to skip them.

        Args:
            diff_test_result (DiffTestResult): The diff test result

        Returns:
            list[str]: The list of diff paths
        """

        indeterministic_regex: set[str] = set()

        args = []
        for original in diff_test_result.originals:
            trial = original["trial"]
            gen = original["gen"]
            trial_basename = os.path.basename(trial)
            original_result = self.trial_to_steps[trial_basename].steps[
                str(gen)
            ]
            args.append([diff_test_result, original_result, self.config])

        with multiprocessing.Pool(num_workers) as pool:
            diff_results = pool.starmap(get_diff_paths_helper, args)

            for diff_item in itertools.chain.from_iterable(diff_results):
                indeterministic_regex.add(diff_item)

        # Handle the case where the name is not deterministic
        common_regex = compute_common_regex(list(indeterministic_regex))

        return common_regex


def get_diff_paths_helper(
    diff_test_result: DiffTestResult,
    original_result: Step,
    config: OperatorConfig,
) -> list[str]:
    """Get the diff paths helper"""
    diff_result = PostDiffTest.check_diff_test_step(
        diff_test_result, original_result, config
    )
    indeterministic_regex = set()
    if isinstance(diff_result, DifferentialOracleResult):
        for diff in diff_result.diff.values():
            if not isinstance(diff, list):
                continue
            for diff_item in diff:
                if not isinstance(diff_item, DiffLevel):
                    continue
                indeterministic_regex.add(diff_item.path())
    return list(indeterministic_regex)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--testrun-dir", type=str, required=True)
    parser.add_argument("--workdir-path", type=str, required=True)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--checkonly", action="store_true")
    args = parser.parse_args()

    # Register custom exception hook
    sys.excepthook = error_handler.handle_excepthook
    threading.excepthook = error_handler.thread_excepthook

    log_filename = "check.log" if args.checkonly else "test.log"
    os.makedirs(args.workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(args.workdir_path, log_filename),
        level=logging.DEBUG,
        filemode="w",
        format="%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s",
    )
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    start = time.time()

    with open(args.config, "r", encoding="utf-8") as config_file:
        config = OperatorConfig(**json.load(config_file))
    p = PostDiffTest(testrun_dir=args.testrun_dir, config=config)
    if not args.checkonly:
        p.post_process(args.workdir_path, num_workers=args.num_workers)
    p.check(args.workdir_path, num_workers=args.num_workers)

    logging.info("Total time: %d seconds", time.time() - start)


if __name__ == "__main__":
    main()
