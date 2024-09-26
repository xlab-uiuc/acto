import json
import logging
import multiprocessing
import multiprocessing.queues
import os
import queue
import subprocess
import time

import kubernetes
import yaml
from chactos.failures.failure import Failure
from chactos.failures.network_chaos import OperatorApplicationPartitionFailure
from chactos.fault_injection_config import FaultInjectionConfig
from chactos.fault_injector import ChaosMeshFaultInjector

from acto.checker.checker_set import CheckerSet
from acto.common import kubernetes_client, print_event
from acto.deploy import Deploy
from acto.input.input import DeterministicInputModel
from acto.kubectl_client.kubectl import KubectlClient
from acto.kubernetes_engine import kind
from acto.lib.operator_config import OperatorConfig
from acto.oracle_handle import OracleHandle
from acto.post_process.post_process import PostProcessor
from acto.runner.runner import Runner
from acto.system_state.kubernetes_system_state import KubernetesSystemState
from acto.trial import Trial
from acto.utils import acto_timer


class ChactosDriver(PostProcessor):
    """Fault injection driver"""

    def __init__(
        self,
        testrun_dir: str,
        work_dir: str,
        operator_config: OperatorConfig,
        fault_injection_config: FaultInjectionConfig,
    ):
        super().__init__(testrun_dir=testrun_dir, config=operator_config)
        # FIXME: why is self.trials a doubly-nested list with only one element?
        self._operator_config = operator_config
        self._fault_injection_config = fault_injection_config
        self._work_dir = work_dir
        self._testrun_dir = testrun_dir

        self.namespace = self.context["namespace"]

        self.kubernetes_provider = kind.Kind(
            acto_namespace=0,
            feature_gates=operator_config.kubernetes_engine.feature_gates,
            num_nodes=operator_config.num_nodes,
            version=operator_config.kubernetes_version,
        )

        # Build an archive to be preloaded
        if not os.path.exists(self._work_dir):
            os.mkdir(self._work_dir)
        container_tool = os.getenv("IMAGE_TOOL", "docker")
        self._images_archive = os.path.join(work_dir, "images.tar")
        if len(self.context["preload_images"]) > 0:
            print_event("Preparing required images...")
            # first make sure images are present locally
            for image in self.context["preload_images"]:
                subprocess.run(
                    [container_tool, "pull", image],
                    stdout=subprocess.DEVNULL,
                    check=True,
                )
            subprocess.run(
                [container_tool, "image", "save", "-o", self._images_archive]
                + list(self.context["preload_images"]),
                stdout=subprocess.DEVNULL,
                check=True,
            )

        self._deployer = Deploy(operator_config.deploy)

    def fault_injection_trial_dir(self, trial_name: str, sequence: int, worker: int):
        """Return the fault injection trial directory"""
        return os.path.join(self._work_dir, f"{trial_name}-fi-{sequence}-worker-{worker}")

    def run(self):
        """Run the fault injection exp"""
        logging.info("Starting fault injection exp")
        operator_selector = self._fault_injection_config.operator_selector
        operator_selector["namespaces"] = [self.namespace]
        app_selector = self._fault_injection_config.application_selector
        app_selector["namespaces"] = [self.namespace]
        failures = []

        logging.info(
            "TODO: Chactos only running on operator app network partition now"
        )
        failures.append(
            OperatorApplicationPartitionFailure(
                operator_selector=operator_selector,
                app_selector=app_selector,
                namespace=self.namespace,
            )
        )

        logging.debug("Trials: [%s]", self.trials)
        logging.debug("Initializing runner list")
        runners: list[DeployChactosDriver] = []

        workqueue: multiprocessing.Queue = multiprocessing.Queue()
        for failure in failures:
            for trial_name, trial in self.trial_to_steps.items():
                workqueue.put([trial_name, trial, failure])


        for worker_id in range(self._operator_config.num_nodes):
            child_process_work_dir = os.path.join(self._work_dir, f"chactos-worker-{worker_id}")
            runner = DeployChactosDriver(
                self._testrun_dir,
                child_process_work_dir,
                self._operator_config,
                self.fault_injection_trial_dir,
                worker_id,
                workqueue
            )
            runners.append(runner)

                    # self.run_trial(
                    #     trial_name=trial_name,
                    #     trial=trial,
                    #     worker_id=worker_id,
                    #     failure=failure,
                    # )

        logging.debug("Launching processes")
        processes = []
        for runner in runners:
            p = multiprocessing.Process(target=runner.run_trial_dist)
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    def apply_cr(
        self,
        cr,
        kubectl_client: KubectlClient,
    ):
        """Apply a CR."""

        cr_file = "cr.yaml"
        with open(cr_file, "w", encoding="utf-8") as f:
            yaml.dump(cr, f)
        p = kubectl_client.kubectl(
            ["apply", "-f", cr_file, "-n", self.namespace],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            logging.error(
                "Failed to apply CR due to error from kubectl"
                + f" (returncode={p.returncode})"
                + f" (stdout={p.stdout})"
                + f" (stderr={p.stderr})"
            )
            return False
        return True

    # TODO: surround run_trial with function that if queue has trial keep
    # TODO: run_trial running

    def run_trial(
        self,
        trial_name: str,
        trial: Trial,
        worker_id: int,
        failure: Failure,
    ):
        """Run a trial, this function can be parallelized

        This function takes a trial from the Acto's normal test run and
        runs it with fault injections.

        With a normal trial with sequence of empty -> m1 -> m2 -> m3 -> m4,
        it may result in multiple fault injection trials:
        empty -> m1 -> m2 -> m3
        empty -> m3 -> m4
        if m2 -> m3 fails in the fault injection trial.
        """

        fault_injection_sequence = 0

        steps = sorted(trial.steps.keys())
        while steps:
            fault_injection_trial_dir = self.fault_injection_trial_dir(
                trial_name=trial_name,
                sequence=fault_injection_sequence,
                worker=worker_id
            )
            os.makedirs(fault_injection_trial_dir, exist_ok=True)

            # Set up the Kubernetes cluster
            kubernetes_cluster_name = self.kubernetes_provider.cluster_name(
                acto_namespace=0, worker_id=worker_id
            )
            kubernetes_context_name = self.kubernetes_provider.get_context_name(
                kubernetes_cluster_name
            )
            kubernetes_config_dict = os.path.join(
                os.path.expanduser("~"), ".kube", kubernetes_context_name
            )
            self.kubernetes_provider.restart_cluster(
                kubernetes_cluster_name, kubernetes_config_dict
            )
            self.kubernetes_provider.load_images(
                self._images_archive, kubernetes_cluster_name
            )
            kubectl_client = KubectlClient(
                kubernetes_config_dict, kubernetes_context_name
            )
            api_client = kubernetes_client(
                kubernetes_config_dict, kubernetes_context_name
            )

            # Set up the operator and dependencies
            deployed = self._deployer.deploy_with_retry(
                kubernetes_config_dict,
                kubernetes_context_name,
                kubectl_client=kubectl_client,
                namespace=self.context["namespace"],
            )
            if not deployed:
                logging.error("Failed to deploy the operator")
                return

            logging.debug("Installing chaos mesh")
            chaosmesh_injector = ChaosMeshFaultInjector()
            chaosmesh_injector.install(
                kube_config=kubernetes_config_dict,
                kube_context=kubernetes_context_name,
            )

            logging.info("Initializing trial runner")
            logging.debug("trial name: [%s]", trial_name)
            trial_dir = os.path.join(self._testrun_dir, trial_name)
            logging.debug("trial dir: [%s]", trial_dir)

            runner = Runner(
                context=self.context,
                trial_dir=trial_dir,
                kubeconfig=kubernetes_config_dict,
                context_name=kubernetes_context_name,
            )

            step_key = steps.pop(0)
            step = trial.steps[step_key]

            logging.debug("Asking runner to run the first input cr")
            inner_steps_generation = 0
            runner.run(
                input_cr=step.snapshot.input_cr,
                generation=inner_steps_generation,
            )

            wait_for_converge(
                kubernetes_client(
                    kubernetes_config_dict, kubernetes_context_name
                ),
                self.context["namespace"],
            )

            logging.debug("Looping on inner steps")
            while steps:
                step_key = steps.pop(0)
                step = trial.steps[step_key]

                logging.debug("Applying failure NOW %s", failure.name())
                failure.apply(kubectl_client)

                logging.debug("Applying next CR")
                chactos_snapshot, err = runner.run(
                    input_cr=step.snapshot.input_cr,
                    generation=inner_steps_generation,
                )
                if err is not None:
                    logging.debug("Error when applying CR: [%s]", err)

                logging.debug("Waiting for CR to converge")
                wait_for_converge(api_client, self.namespace, hard_timeout=180)

                logging.debug("Clearning up failure %s", failure.name())
                failure.cleanup(kubectl_client)

                logging.debug("Waiting for cleanup to converge")
                wait_for_converge(api_client, self.namespace)

                logging.debug("Acquiring oracle.")
                # oracle
                deprecated_system_state = KubernetesSystemState.from_api_client(
                    api_client=api_client,
                    namespace=self.namespace,
                )

                logging.debug("Acquiring system states from runner.")
                # system_state = runner.collect_system_state()

                logging.info("Initializing pre reqs for checker")
                with open(
                    self._operator_config.seed_custom_resource,
                    "r",
                    encoding="utf-8",
                ) as cr_file:
                    seed = yaml.load(cr_file, Loader=yaml.FullLoader)
                seed["metadata"]["name"] = "test-cluster"
                det_inputmodel = DeterministicInputModel(
                    crd=self.context["crd"]["body"],
                    seed_input=seed,
                    example_dir=self._operator_config.example_dir,
                    num_workers=1,  # TODO: add this to chactos args?
                    num_cases=1,  # TODO: add this too?
                    kubernetes_version=self._operator_config.kubernetes_version,
                    custom_module_path=self._operator_config.custom_module,
                )

                checking_snapshots = [step.snapshot, chactos_snapshot]
                oracle_handle = OracleHandle(
                    kubectl_client=kubectl_client,
                    k8s_client=kubernetes_client,
                    namespace=self.context["namespace"],
                    snapshots=checking_snapshots,
                )

                logging.info("Initializing checker")
                checker = CheckerSet(
                    context=self.context,
                    trial_dir=trial_dir,
                    input_model=det_inputmodel,
                    oracle_handle=oracle_handle,
                )

                oracle_results = checker.check(
                    snapshot=chactos_snapshot,
                    prev_snapshot=step.snapshot,
                    generation=inner_steps_generation,
                )

                logging.info("Finished checking oracle:")
                logging.debug(
                    "Dumping oracle to json regardless of healthiness"
                )
                with open(
                    os.path.join(
                        fault_injection_trial_dir,
                        f"oracle-{inner_steps_generation}.json",
                    ),
                    "w",
                    encoding="utf-8",
                ) as oracle_json:
                    json.dump(oracle_results.model_dump(), oracle_json)

                health = deprecated_system_state.check_health()
                if not health.is_healthy():
                    logging.error("System is not healthy %s", health)
                    break

                inner_steps_generation += 1

            fault_injection_sequence += 1


def wait_for_converge(api_client, namespace, wait_time=60, hard_timeout=600):
    """This function blocks until the system converges. It keeps
        watching for incoming events. If there is no event within
        60 seconds, the system is considered to have converged.

    Args:
        hard_timeout: the maximal wait time for system convergence

    Returns:
        True if the system converge within the hard timeout
    """

    start_timestamp = time.time()
    logging.info("Waiting for system to converge... ")

    core_v1_api = kubernetes.client.CoreV1Api(api_client)
    event_stream = core_v1_api.list_namespaced_event(
        namespace, _preload_content=False, watch=True
    )

    combined_event_queue = multiprocessing.Queue(maxsize=0)
    timer_hard_timeout = acto_timer.ActoTimer(
        hard_timeout, combined_event_queue, "timeout"
    )
    watch_process = multiprocessing.Process(
        target=watch_system_events,
        args=(event_stream, combined_event_queue),
    )

    timer_hard_timeout.start()
    watch_process.start()

    converge = True
    while True:
        try:
            event = combined_event_queue.get(timeout=wait_time)
            if event == "timeout":
                converge = False
                break
        except queue.Empty:
            ready = True
            app_v1_api = kubernetes.client.AppsV1Api(api_client)
            statefulsets = [
                i.to_dict()
                for i in app_v1_api.list_namespaced_stateful_set(
                    namespace
                ).items
            ]
            deployments = [
                i.to_dict()
                for i in app_v1_api.list_namespaced_deployment(namespace).items
            ]
            daemonsets = [
                i.to_dict()
                for i in app_v1_api.list_namespaced_daemon_set(namespace).items
            ]

            for sfs in statefulsets:
                if (
                    sfs["status"]["ready_replicas"] is None
                    and sfs["status"]["replicas"] == 0
                ):
                    # replicas could be 0
                    continue
                if sfs["status"]["replicas"] != sfs["status"]["ready_replicas"]:
                    ready = False
                    logging.info(
                        "Statefulset %s is not ready yet",
                        sfs["metadata"]["name"],
                    )
                    break
                if sfs["spec"]["replicas"] != sfs["status"]["replicas"]:
                    ready = False
                    logging.info(
                        "Statefulset %s is not ready yet",
                        sfs["metadata"]["name"],
                    )
                    break

            for dp in deployments:
                if dp["spec"]["replicas"] == 0:
                    continue

                if dp["status"]["replicas"] != dp["status"]["ready_replicas"]:
                    ready = False
                    logging.info(
                        "Deployment %s is not ready yet",
                        dp["metadata"]["name"],
                    )
                    break

                for condition in dp["status"]["conditions"]:
                    if (
                        condition["type"] == "Available"
                        and condition["status"] != "True"
                    ):
                        ready = False
                        logging.info(
                            "Deployment %s is not ready yet",
                            dp["metadata"]["name"],
                        )
                        break

                    if (
                        condition["type"] == "Progressing"
                        and condition["status"] != "True"
                    ):
                        ready = False
                        logging.info(
                            "Deployment %s is not ready yet",
                            dp["metadata"]["name"],
                        )
                        break

            for ds in daemonsets:
                if (
                    ds["status"]["number_ready"]
                    != ds["status"]["current_number_scheduled"]
                ):
                    ready = False
                    logging.info(
                        "Daemonset %s is not ready yet",
                        ds["metadata"]["name"],
                    )
                    break
                if (
                    ds["status"]["desired_number_scheduled"]
                    != ds["status"]["number_ready"]
                ):
                    ready = False
                    logging.info(
                        "Daemonset %s is not ready yet",
                        ds["metadata"]["name"],
                    )
                    break
                if (
                    "updated_number_scheduled" in ds["status"]
                    and ds["status"]["updated_number_scheduled"]
                    != ds["status"]["desired_number_scheduled"]
                ):
                    ready = False
                    logging.info(
                        "Daemonset %s is not ready yet",
                        ds["metadata"]["name"],
                    )
                    break

            if ready:
                # only stop waiting if all deployments and statefulsets are ready
                # else, keep waiting until ready or hard timeout
                break

    event_stream.close()
    timer_hard_timeout.cancel()
    watch_process.terminate()

    time_elapsed = time.strftime(
        "%H:%M:%S", time.gmtime(time.time() - start_timestamp)
    )
    if converge:
        logging.info("System took %s to converge", time_elapsed)
        return True
    else:
        logging.error(
            "System failed to converge within %d seconds", hard_timeout
        )
        return False


def watch_system_events(event_stream, q: multiprocessing.Queue):
    """A process that watches namespaced events"""
    for _ in event_stream:
        try:
            q.put("event")
        except (ValueError, AssertionError):
            pass


class DeployChactosDriver(ChactosDriver):
    """
    The distributed wrapper for running in multi processes
    """
    def __init__(
        self,
        testrun_dir: str,
        work_dir: str,
        operator_config: OperatorConfig,
        fault_injection_config: FaultInjectionConfig,
        worker_id: int,
        workqueue: multiprocessing.Queue
    ):
        super().__init__(
            testrun_dir,
            work_dir,
            operator_config,
            fault_injection_config
        )
        self.worker_id = worker_id
        self.workqueue = workqueue

        #FIXME: improve SE practice here
        self.trial = None
        self.trial_name = None
        self.failure = None

    def run_trial_dist(
        self,
    ):
        """Run a trial, this function can be parallelized

        This function takes a trial from the Acto's normal test run and
        runs it with fault injections.

        With a normal trial with sequence of empty -> m1 -> m2 -> m3 -> m4,
        it may result in multiple fault injection trials:
        empty -> m1 -> m2 -> m3
        empty -> m3 -> m4
        if m2 -> m3 fails in the fault injection trial.
        """
        while True:
            try:
                job_details = self.workqueue.get(block=False)
                self.trial = job_details[1]
                self.trial_name = job_details[0]
                self.failure = job_details[2]
            except queue.Empty:
                break

            fault_injection_sequence = 0

            steps = sorted(self.trial.steps.keys())
            while steps:
                fault_injection_trial_dir = self.fault_injection_trial_dir(
                    trial_name=self.trial_name,
                    sequence=fault_injection_sequence,
                    worker=self.worker_id
                )
                os.makedirs(fault_injection_trial_dir, exist_ok=True)

                # Set up the Kubernetes cluster
                kubernetes_cluster_name = self.kubernetes_provider.cluster_name(
                    acto_namespace=0, worker_id=self.worker_id
                )
                kubernetes_context_name = self.kubernetes_provider.get_context_name(
                    kubernetes_cluster_name
                )
                kubernetes_config_dict = os.path.join(
                    os.path.expanduser("~"), ".kube", kubernetes_context_name
                )
                self.kubernetes_provider.restart_cluster(
                    kubernetes_cluster_name, kubernetes_config_dict
                )
                self.kubernetes_provider.load_images(
                    self._images_archive, kubernetes_cluster_name
                )
                kubectl_client = KubectlClient(
                    kubernetes_config_dict, kubernetes_context_name
                )
                api_client = kubernetes_client(
                    kubernetes_config_dict, kubernetes_context_name
                )

                # Set up the operator and dependencies
                deployed = self._deployer.deploy_with_retry(
                    kubernetes_config_dict,
                    kubernetes_context_name,
                    kubectl_client=kubectl_client,
                    namespace=self.context["namespace"],
                )
                if not deployed:
                    logging.error("Failed to deploy the operator")
                    return

                logging.debug("Installing chaos mesh")
                chaosmesh_injector = ChaosMeshFaultInjector()
                chaosmesh_injector.install(
                    kube_config=kubernetes_config_dict,
                    kube_context=kubernetes_context_name,
                )

                logging.info("Initializing trial runner")
                logging.debug("trial name: [%s]", self.trial_name)
                trial_dir = os.path.join(self._testrun_dir, self.trial_name)
                logging.debug("trial dir: [%s]", trial_dir)

                runner = Runner(
                    context=self.context,
                    trial_dir=trial_dir,
                    kubeconfig=kubernetes_config_dict,
                    context_name=kubernetes_context_name,
                )

                step_key = steps.pop(0)
                step = self.trial.steps[step_key]

                logging.debug("Asking runner to run the first input cr")
                inner_steps_generation = 0
                runner.run(
                    input_cr=step.snapshot.input_cr,
                    generation=inner_steps_generation,
                )

                wait_for_converge(
                    kubernetes_client(
                        kubernetes_config_dict, kubernetes_context_name
                    ),
                    self.context["namespace"],
                )

                logging.debug("Looping on inner steps")
                while steps:
                    step_key = steps.pop(0)
                    step = self.trial.steps[step_key]

                    logging.debug("Applying failure NOW %s", self.failure.name())
                    self.failure.apply(kubectl_client)

                    logging.debug("Applying next CR")
                    chactos_snapshot, err = runner.run(
                        input_cr=step.snapshot.input_cr,
                        generation=inner_steps_generation,
                    )
                    if err is not None:
                        logging.debug("Error when applying CR: [%s]", err)

                    logging.debug("Waiting for CR to converge")
                    wait_for_converge(api_client, self.namespace, hard_timeout=180)

                    logging.debug("Clearning up failure %s", self.failure.name())
                    self.failure.cleanup(kubectl_client)

                    logging.debug("Waiting for cleanup to converge")
                    wait_for_converge(api_client, self.namespace)

                    logging.debug("Acquiring oracle.")
                    # oracle
                    deprecated_system_state = KubernetesSystemState.from_api_client(
                        api_client=api_client,
                        namespace=self.namespace,
                    )

                    logging.debug("Acquiring system states from runner.")
                    # system_state = runner.collect_system_state()

                    logging.info("Initializing pre reqs for checker")
                    with open(
                        self._operator_config.seed_custom_resource,
                        "r",
                        encoding="utf-8",
                    ) as cr_file:
                        seed = yaml.load(cr_file, Loader=yaml.FullLoader)
                    seed["metadata"]["name"] = "test-cluster"
                    det_inputmodel = DeterministicInputModel(
                        crd=self.context["crd"]["body"],
                        seed_input=seed,
                        example_dir=self._operator_config.example_dir,
                        num_workers=1,  # TODO: add this to chactos args?
                        num_cases=1,  # TODO: add this too?
                        kubernetes_version=self._operator_config.kubernetes_version,
                        custom_module_path=self._operator_config.custom_module,
                    )

                    checking_snapshots = [step.snapshot, chactos_snapshot]
                    oracle_handle = OracleHandle(
                        kubectl_client=kubectl_client,
                        k8s_client=kubernetes_client,
                        namespace=self.context["namespace"],
                        snapshots=checking_snapshots,
                    )

                    logging.info("Initializing checker")
                    checker = CheckerSet(
                        context=self.context,
                        trial_dir=trial_dir,
                        input_model=det_inputmodel,
                        oracle_handle=oracle_handle,
                    )

                    oracle_results = checker.check(
                        snapshot=chactos_snapshot,
                        prev_snapshot=step.snapshot,
                        generation=inner_steps_generation,
                    )

                    logging.info("Finished checking oracle:")
                    logging.debug(
                        "Dumping oracle to json regardless of healthiness"
                    )
                    with open(
                        os.path.join(
                            fault_injection_trial_dir,
                            f"oracle-{inner_steps_generation}.json",
                        ),
                        "w",
                        encoding="utf-8",
                    ) as oracle_json:
                        json.dump(oracle_results.model_dump(), oracle_json)

                    health = deprecated_system_state.check_health()
                    if not health.is_healthy():
                        logging.error("System is not healthy %s", health)
                        break

                    inner_steps_generation += 1

                fault_injection_sequence += 1
