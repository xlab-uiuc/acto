import glob
import logging
import multiprocessing
import os
import queue
import time

import kubernetes
import yaml
import json

from acto import constant
from acto.common import kubernetes_client
from acto.deploy import Deploy
from acto.kubectl_client.helm import Helm
from acto.kubectl_client.kubectl import KubectlClient
from acto.post_process.post_process import PostProcessor
from acto.kubernetes_engine.base import KubernetesEngine
from acto.kubernetes_engine.kind import Kind
from acto.system_state.kubernetes_system_state import KubernetesSystemState
from acto.utils import acto_timer
from chactos.failures.file_chaos import (
    ApplicationFileDelay,
    ApplicationFileFailure,
)
from chactos.failures.network_chaos import OperatorApplicationPartitionFailure
from chactos.fault_injection_config import FaultInjectionConfig


def load_inputs_from_dir(dir_: str) -> list[object]:
    """Load inputs from a directory"""
    inputs = []
    files = sorted(glob.glob(f"{dir_}/input-*.yaml"))
    logging.info("Loading %d inputs from %s", len(files), dir_)
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            inputs.append(yaml.load(f, Loader=yaml.FullLoader))

    return inputs


class ExperimentDriver:
    """Driver class for running fault injection experiments."""

    def __init__(self, operator_config: FaultInjectionConfig, worker_id: int):
        self._worker_id = worker_id
        self._operator_config = operator_config

    def run(self):
        """Run the experiment."""
        operator_selector = self._operator_config.operator_selector
        operator_selector["namespaces"] = [constant.CONST.ACTO_NAMESPACE]
        app_selector = self._operator_config.application_selector
        app_selector["namespaces"] = [constant.CONST.ACTO_NAMESPACE]
        failures = []
        failures.append(
            ApplicationFileFailure(
                app_selector=app_selector,
                data_dir=self._operator_config.application_data_dir,
            )
        )
        failures.append(
            OperatorApplicationPartitionFailure(
                operator_selector=operator_selector,
                app_selector=app_selector,
            )
        )
        failures.append(
            ApplicationFileDelay(
                app_selector=app_selector,
                data_dir=self._operator_config.application_data_dir,
            )
        )
        for failure in failures:
            logging.info("Applying failure %s", failure.name())
            k8s_cluster_engine: KubernetesEngine = Kind(
                0, num_nodes=self._operator_config.kubernetes.num_nodes
            )
            cluster_name = f"acto-cluster-{self._worker_id}"
            kubecontext = k8s_cluster_engine.get_context_name(cluster_name)
            kubeconfig = os.path.join(
                os.path.expanduser("~"), ".kube", kubecontext
            )
            k8s_cluster_engine.restart_cluster(cluster_name, kubeconfig)
            apiclient = kubernetes_client(kubeconfig, kubecontext)
            kubectl_client = KubectlClient(kubeconfig, kubecontext)

            # Deploy dependencies and operator
            helm_client = Helm(kubeconfig, kubecontext)
            p = helm_client.install(
                release_name="chaos-mesh",
                chart="chaos-mesh",
                namespace="chaos-mesh",
                repo="https://charts.chaos-mesh.org",
                args=[
                    "--set",
                    "chaosDaemon.runtime=containerd",
                    "--set",
                    "chaosDaemon.socketPath=/run/containerd/containerd.sock",
                    "--version",
                    "2.6.3",
                ],
            )
            if p.returncode != 0:
                raise RuntimeError("Failed to install chaos-mesh", p.stderr)

            deployer = Deploy(self._operator_config.deploy)
            deployer.deploy(
                kubeconfig,
                kubecontext,
                kubectl_client=KubectlClient(
                    kubeconfig=kubeconfig, context_name=kubecontext
                ),
                namespace=constant.CONST.ACTO_NAMESPACE,
            )

            crs = load_inputs_from_dir(self._operator_config.input_dir)

            cr = crs.pop(0)
            self.apply_cr(cr, kubectl_client)
            converged = wait_for_converge(
                apiclient, constant.CONST.ACTO_NAMESPACE
            )

            if not converged:
                logging.error("Failed to converge")
                return

            while crs:
                failure.apply(kubectl_client)

                cr = crs.pop(0)
                self.apply_cr(cr, kubectl_client)
                converged = wait_for_converge(
                    apiclient, constant.CONST.ACTO_NAMESPACE, hard_timeout=180
                )

                failure.cleanup(kubectl_client)
                converged = wait_for_converge(
                    apiclient, constant.CONST.ACTO_NAMESPACE
                )

                # oracle
                system_state = KubernetesSystemState.from_api_client(
                    api_client=apiclient,
                    namespace=constant.CONST.ACTO_NAMESPACE,
                )
                health = system_state.check_health()
                if not health.is_healthy():
                    logging.error("System is not healthy %s", health)
                    return

    def apply_cr(
        self,
        cr: dict,
        kubectl_client: KubectlClient,
    ):
        """Apply a CR."""
        cr_file = "cr.yaml"
        with open(cr_file, "w", encoding="utf-8") as f:
            yaml.dump(cr, f)
        p = kubectl_client.kubectl(
            ["apply", "-f", cr_file, "-n", constant.CONST.ACTO_NAMESPACE]
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


class ChactosDriver(PostProcessor):
    """Fault injection driver"""
    def __init__(self, testrun_dir: str, operator_config: FaultInjectionConfig, worker_id: int):
        super().__init__(testrun_dir=testrun_dir, config=operator_config)
        self._worker_id = worker_id
        self._operator_config = operator_config

    def fetch_crs_from_trials(self) -> dict[str, object]:
        """
        Fetches crs from trials and put them into a list of string yamls
        """

        # TODO: IO ops exists program prematurely??
        crs = {}
        trials = self.trial_to_steps

        for trial_names in trials:
            input_crs = []
            steps = trials[trial_names].steps
            for tup in steps.items():
                step = tup[1]
                input_cr = step.snapshot.input_cr
                input_crs.append(input_cr)
            crs[trial_names] = input_crs
            # print(len(crs[trial_names]))
        return crs


    def run(self):
        operator_selector = self._operator_config.operator_selector
        operator_selector["namespaces"] = [constant.CONST.ACTO_NAMESPACE]
        app_selector = self._operator_config.application_selector
        app_selector["namespaces"] = [constant.CONST.ACTO_NAMESPACE]
        failures = []
        failures.append(
            OperatorApplicationPartitionFailure(
                operator_selector=operator_selector,
                app_selector=app_selector,
            )
        )

        for failure in failures:
            logging.info("Applying failure %s", failure.name())
            k8s_cluster_engine: KubernetesEngine = Kind(
                0, num_nodes=self._operator_config.kubernetes.num_nodes
            )
            cluster_name = f"acto-cluster-{self._worker_id}"
            kubecontext = k8s_cluster_engine.get_context_name(cluster_name)
            kubeconfig = os.path.join(
                os.path.expanduser("~"), ".kube", kubecontext
            )
            k8s_cluster_engine.restart_cluster(cluster_name, kubeconfig)
            apiclient = kubernetes_client(kubeconfig, kubecontext)
            kubectl_client = KubectlClient(kubeconfig, kubecontext)

            # Deploy dependencies and operator
            helm_client = Helm(kubeconfig, kubecontext)
            p = helm_client.install(
                release_name="chaos-mesh",
                chart="chaos-mesh",
                namespace="chaos-mesh",
                repo="https://charts.chaos-mesh.org",
                args=[
                    "--set",
                    "chaosDaemon.runtime=containerd",
                    "--set",
                    "chaosDaemon.socketPath=/run/containerd/containerd.sock",
                    "--version",
                    "2.6.3",
                ],
            )
            if p.returncode != 0:
                raise RuntimeError("Failed to install chaos-mesh", p.stderr)

            deployer = Deploy(self._operator_config.deploy)
            deployer.deploy(
                kubeconfig,
                kubecontext,
                kubectl_client=KubectlClient(
                    kubeconfig=kubeconfig, context_name=kubecontext
                ),
                namespace=constant.CONST.ACTO_NAMESPACE,
            )

            # crs = load_inputs_from_dir(self._operator_config.input_dir)
            crs = self.fetch_crs_from_trials()
            crs = crs[crs.keys()[0]]

            cr = crs.pop(0)
            self.apply_cr(cr, kubectl_client)
            converged = wait_for_converge(
                apiclient, constant.CONST.ACTO_NAMESPACE
            )

            if not converged:
                logging.error("Failed to converge")
                return

            while crs:
                failure.apply(kubectl_client)

                cr = crs.pop(0)
                self.apply_cr(cr, kubectl_client)
                converged = wait_for_converge(
                    apiclient, constant.CONST.ACTO_NAMESPACE, hard_timeout=180
                )

                failure.cleanup(kubectl_client)
                converged = wait_for_converge(
                    apiclient, constant.CONST.ACTO_NAMESPACE
                )

                # oracle
                system_state = KubernetesSystemState.from_api_client(
                    api_client=apiclient,
                    namespace=constant.CONST.ACTO_NAMESPACE,
                )
                health = system_state.check_health()
                if not health.is_healthy():
                    logging.error("System is not healthy %s", health)
                    return


    # TODO: gather trial dirs like PostDiffTest
    # TODO: rewrite ExperimentDriver.run in this class to run the trials with
    # trial dir instead of local dir
    # TODO: run only network partition first


    def apply_cr(
        self,
        cr: str,
        kubectl_client: KubectlClient,
    ):
        """Apply a CR."""
        cr_file = "cr.yaml"
        python_dict = json.loads(cr)

        with open(cr_file, "w", encoding="utf-8") as f:
            yaml.dump(python_dict, f)

        p = kubectl_client.kubectl(
            ["apply", "-f", cr_file, "-n", constant.CONST.ACTO_NAMESPACE]
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
