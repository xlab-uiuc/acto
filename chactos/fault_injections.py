import logging
import multiprocessing
import os
import queue
import subprocess
import time

import kubernetes
import yaml

from acto.common import kubernetes_client, print_event
from acto.deploy import Deploy
from acto.kubectl_client.kubectl import KubectlClient
from acto.kubernetes_engine import kind
from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_process import PostProcessor
from acto.system_state.kubernetes_system_state import KubernetesSystemState
from acto.trial import Trial
from acto.utils import acto_timer
from chactos.failures.failure import Failure
from chactos.failures.network_chaos import OperatorApplicationPartitionFailure
from chactos.fault_injection_config import FaultInjectionConfig


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
        self._operator_config = operator_config
        self._fault_injection_config = fault_injection_config
        self._work_dir = work_dir

        self.namespace = self.context["namespace"]

        self.kubernetes_provider = kind.Kind(
            acto_namespace=0,
            feature_gates=operator_config.kubernetes_engine.feature_gates,
            num_nodes=operator_config.num_nodes,
            version=operator_config.kubernetes_version,
        )

        # Build an archive to be preloaded
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

    def fault_injection_trial_dir(self, trial_name: str, sequence: int):
        """Return the fault injection trial directory"""
        return os.path.join(self._work_dir, f"{trial_name}-fi-{sequence}")

    def run(self):
        """Run the fault injection exp"""
        operator_selector = self._fault_injection_config.operator_selector
        operator_selector["namespaces"] = [self.namespace]
        app_selector = self._fault_injection_config.application_selector
        app_selector["namespaces"] = [self.namespace]
        failures = []
        failures.append(
            OperatorApplicationPartitionFailure(
                operator_selector=operator_selector,
                app_selector=app_selector,
                namespace=self.namespace,
            )
        )

        for failure in failures:
            for trial_name, trial in self.trials.items():
                for worker_id in range(self._operator_config.num_nodes):
                    self.run_trial(
                        trial_name=trial_name,
                        trial=trial,
                        worker_id=worker_id,
                        failure=failure,
                    )

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
                trial_name=trial_name, sequence=fault_injection_sequence
            )
            os.makedirs(fault_injection_trial_dir, exist_ok=True)

            # Set up the Kubernetes cluster
            kubernetes_cluster_name = self.kubernetes_provider.cluster_name(
                acto_namespace=0, worker_id=worker_id
            )
            kubernetes_context = self.kubernetes_provider.get_context_name(
                kubernetes_cluster_name
            )
            kubeconfig = os.path.join(
                os.path.expanduser("~"), ".kube", kubernetes_context
            )
            self.kubernetes_provider.restart_cluster(
                kubernetes_cluster_name, kubeconfig
            )
            self.kubernetes_provider.load_images(
                self._images_archive, kubernetes_cluster_name
            )
            kubectl_client = KubectlClient(kubeconfig, kubernetes_context)
            api_client = kubernetes_client(kubeconfig, kubernetes_context)

            # Set up the operator and dependencies
            deployed = self._deployer.deploy_with_retry(
                kubeconfig,
                kubernetes_context,
                kubectl_client=kubectl_client,
                namespace=self.context["namespace"],
            )
            if not deployed:
                logging.error("Failed to deploy the operator")
                return

            step_key = steps.pop(0)
            step = trial.steps[step_key]
            self.apply_cr(step.snapshot.input_cr, kubectl_client)
            wait_for_converge(
                kubernetes_client(kubeconfig, kubernetes_context),
                self.context["namespace"],
            )
            while steps:
                step_key = steps.pop(0)
                step = trial.steps[step_key]

                logging.debug("Applying failure NOW %s", failure.name())
                failure.apply(kubectl_client)

                logging.debug("Applying next CR")
                self.apply_cr(step.snapshot.input_cr, kubectl_client)

                logging.debug("Waiting for CR to converge")
                converged = wait_for_converge(
                    api_client, self.namespace, hard_timeout=180
                )

                logging.debug("Clearning up failure %s", failure.name())
                failure.cleanup(kubectl_client)

                logging.debug("Waiting for cleanup to converge")
                converged = wait_for_converge(api_client, self.namespace)

                logging.debug("Acquiring oracle.")
                # oracle
                system_state = KubernetesSystemState.from_api_client(
                    api_client=api_client,
                    namespace=self.namespace,
                )
                health = system_state.check_health()
                if not health.is_healthy():
                    logging.error("System is not healthy %s", health)
                    break

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
