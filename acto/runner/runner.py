"""Runner module for Acto"""

import base64
import multiprocessing
import queue
import subprocess
import time
from typing import Callable, Optional

import kubernetes
import kubernetes.client.models as kubernetes_models
import yaml

from acto import snapshot
from acto.common import kubernetes_client
from acto.kubectl_client import KubectlClient
from acto.utils import acto_timer, get_thread_logger

RunnerHookType = Callable[[kubernetes.client.ApiClient], None]
CustomSystemStateHookType = Callable[
    [kubernetes.client.ApiClient, str, int], dict
]


class Runner:
    """Runner class for Acto.
    This class is used to run the cmd and collect system state,
    delta, operator log, events and input files.
    """

    def __init__(
        self,
        context: dict,
        trial_dir: str,
        kubeconfig: str,
        context_name: str,
        custom_system_state_f: Optional[Callable[..., dict]] = None,
        wait_time: int = 45,
        operator_container_name: Optional[str] = None,
    ):
        self.namespace = context["namespace"]
        self.crd_metainfo: dict = context["crd"]
        self.trial_dir = trial_dir
        self.kubeconfig = kubeconfig
        self.context_name = context_name
        self.operator_container_name = operator_container_name
        self.wait_time = wait_time
        self.log_length = 0

        self.kubectl_client = KubectlClient(kubeconfig, context_name)

        apiclient = kubernetes_client(kubeconfig, context_name)
        self.apiclient = apiclient
        self.core_v1_api = kubernetes.client.CoreV1Api(apiclient)
        self.app_v1_api = kubernetes.client.AppsV1Api(apiclient)
        self.batch_v1_api = kubernetes.client.BatchV1Api(apiclient)
        self.custom_object_api = kubernetes.client.CustomObjectsApi(apiclient)
        self.policy_v1_api = kubernetes.client.PolicyV1Api(apiclient)
        self.networking_v1_api = kubernetes.client.NetworkingV1Api(apiclient)
        self.rbac_authorization_v1_api = (
            kubernetes.client.RbacAuthorizationV1Api(apiclient)
        )
        self.storage_v1_api = kubernetes.client.StorageV1Api(apiclient)
        self.scheduling_v1_api = kubernetes.client.SchedulingV1Api(apiclient)
        self.resource_methods = {
            "pod": self.core_v1_api.list_namespaced_pod,
            "stateful_set": self.app_v1_api.list_namespaced_stateful_set,
            "deployment": self.app_v1_api.list_namespaced_deployment,
            "daemon_set": self.app_v1_api.list_namespaced_daemon_set,
            "config_map": self.core_v1_api.list_namespaced_config_map,
            "service": self.core_v1_api.list_namespaced_service,
            "pvc": self.core_v1_api.list_namespaced_persistent_volume_claim,
            "cronjob": self.batch_v1_api.list_namespaced_cron_job,
            "ingress": self.networking_v1_api.list_namespaced_ingress,
            "network_policy": self.networking_v1_api.list_namespaced_network_policy,
            "pod_disruption_budget": self.policy_v1_api.list_namespaced_pod_disruption_budget,
            "secret": self.core_v1_api.list_namespaced_secret,
            "endpoints": self.core_v1_api.list_namespaced_endpoints,
            "service_account": self.core_v1_api.list_namespaced_service_account,
            "job": self.batch_v1_api.list_namespaced_job,
            "role": self.rbac_authorization_v1_api.list_namespaced_role,
            "role_binding": self.rbac_authorization_v1_api.list_namespaced_role_binding,
        }

        self.mp_ctx = multiprocessing.get_context("fork")

        self._custom_system_state_f = custom_system_state_f

    def run(
        self,
        input_cr: dict,
        generation: int,
        hooks: Optional[list[RunnerHookType]] = None,
    ) -> tuple[snapshot.Snapshot, bool]:
        """Simply run the cmd and dumps system_state, delta, operator log,
        events and input files without checking.
        The function blocks until system converges.

            Args:
                input_cr: CR to be applied in the format of dict
                generation: the generation number of the input file
                hooks: a list of hooks to be called before applying the CR

            Returns:
                result, err
        """
        logger = get_thread_logger(with_prefix=True)

        # call user-defined hooks
        if hooks is not None:
            for hook in hooks:
                hook(self.apiclient)

        mutated_filename = snapshot.input_cr_path(self.trial_dir, generation)
        with open(mutated_filename, "w", encoding="utf-8") as mutated_cr_file:
            yaml.dump(input_cr, mutated_cr_file)

        cmd = ["apply", "-f", mutated_filename, "-n", self.namespace]

        # submit the CR
        cli_result = self.kubectl_client.kubectl(
            cmd, capture_output=True, text=True
        )
        logger.debug("STDOUT: %s", cli_result.stdout)
        logger.debug("STDERR: %s", cli_result.stderr)

        if cli_result.returncode != 0:
            logger.error(
                "kubectl apply failed with return code %d",
                cli_result.returncode,
            )
            logger.error("STDOUT: %s", cli_result.stdout)
            logger.error("STDERR: %s", cli_result.stderr)
            s = snapshot.Snapshot(
                input_cr=input_cr,
                cli_result=self.collect_cli_result(cli_result),
                system_state={},
                operator_log=[],
                events={},
                not_ready_pods_logs=None,
                generation=generation,
            )
            s.dump(self.trial_dir)
            return s, True

        err = None

        try:
            err = self.wait_for_system_converge()
        except (KeyError, ValueError) as e:
            logger.error(
                "Bug! Exception raised when waiting for converge.", exc_info=e
            )
            system_state = {}
            operator_log = ["Bug! Exception raised when waiting for converge."]
            err = True

        # when client API raise an exception, catch it and write to log instead of crashing Acto
        try:
            if self._custom_system_state_f is not None:
                _ = self._custom_system_state_f(
                    self.apiclient, self.trial_dir, generation
                )
            system_state = self.collect_system_state()
            operator_log = self.collect_operator_log()
        except (KeyError, ValueError) as e:
            logger.error(
                "Bug! Exception raised when waiting for converge.", exc_info=e
            )
            system_state = {}
            operator_log = ["Bug! Exception raised when waiting for converge."]
            err = True
        events = self.collect_events()
        unready_pod_logs = self.collect_not_ready_pods_logs()

        s = snapshot.Snapshot(
            input_cr=input_cr,
            cli_result=self.collect_cli_result(cli_result),
            system_state=system_state,
            operator_log=operator_log,
            events=events,
            not_ready_pods_logs=unready_pod_logs,
            generation=generation,
        )
        return s, err

    def run_without_collect(self, seed_file: str):
        """Simply run the cmd without collecting system_state"""
        cmd = ["apply", "-f", seed_file, "-n", self.namespace]
        _ = self.kubectl_client.kubectl(cmd)

        try:
            _ = self.wait_for_system_converge()
        except (KeyError, ValueError) as e:
            logger = get_thread_logger(with_prefix=True)
            logger.error(
                "Bug! Exception raised when waiting for converge.", exc_info=e
            )

    def delete(self, generation: int) -> bool:
        """Delete the mutated CR"""
        logger = get_thread_logger(with_prefix=True)
        start = time.time()
        mutated_filename = snapshot.input_cr_path(self.trial_dir, generation)
        logger.info("Deleting: %s", mutated_filename)

        cmd = ["delete", "-f", mutated_filename, "-n", self.namespace]
        try:
            cli_result = self.kubectl_client.kubectl(
                cmd, capture_output=True, text=True, timeout=120
            )
        except subprocess.TimeoutExpired as _:
            logger.error("kubectl delete timeout.")
            return True

        logger.debug("STDOUT: %s", cli_result.stdout)
        logger.debug("STDERR: %s", cli_result.stderr)

        for __ in range(0, 600):
            crs = self.__get_custom_resources(
                self.namespace,
                self.crd_metainfo["group"],
                self.crd_metainfo["version"],
                self.crd_metainfo["plural"],
            )
            if len(crs) == 0:
                break
            time.sleep(1)

        if len(crs) != 0:
            logger.error("Failed to delete custom resource.")
            return True
        else:
            logger.info(
                "Successfully deleted custom resource in %ds.",
                time.time() - start,
            )
            return False

    def collect_system_state(self) -> dict:
        """Queries resources in the test namespace, computes delta

        Args:
        """
        logger = get_thread_logger(with_prefix=True)

        resources = {}

        for resource, method in self.resource_methods.items():
            resources[resource] = self.__get_all_objects(method)
            if resource == "pod":
                # put pods managed by deployment / replicasets into an array
                all_pods = self.__get_all_objects(method)
                (
                    resources["deployment_pods"],
                    resources["daemonset_pods"],
                    resources["pod"],
                ) = group_pods(all_pods)
            elif resource == "secret":
                resources[resource] = decode_secret_data(resources[resource])

        current_cr = self.__get_custom_resources(
            self.namespace,
            self.crd_metainfo["group"],
            self.crd_metainfo["version"],
            self.crd_metainfo["plural"],
        )
        logger.debug(current_cr)

        resources["custom_resource_spec"] = (
            current_cr["test-cluster"]["spec"]
            if "spec" in current_cr["test-cluster"]
            else None
        )
        resources["custom_resource_status"] = (
            current_cr["test-cluster"]["status"]
            if "status" in current_cr["test-cluster"]
            else None
        )

        return resources

    def collect_operator_log(self) -> list:
        """Queries operator log in the test namespace

        Args:
        """
        logger = get_thread_logger(with_prefix=True)

        operator_pod_list = self.core_v1_api.list_namespaced_pod(
            namespace=self.namespace,
            watch=False,
            label_selector="acto/tag=operator-pod",
        ).items

        if len(operator_pod_list) >= 1:
            logger.debug(
                "Got operator pod: pod name: %s",
                operator_pod_list[0].metadata.name,
            )
        else:
            logger.error("Failed to find operator pod")

        if self.operator_container_name is not None:
            log = self.core_v1_api.read_namespaced_pod_log(
                name=operator_pod_list[0].metadata.name,
                namespace=self.namespace,
                container=self.operator_container_name,
            )
        else:
            if len(operator_pod_list[0].spec.containers) > 1:
                logger.error(
                    "Multiple containers detected, please specify the target operator container"
                )
            log = self.core_v1_api.read_namespaced_pod_log(
                name=operator_pod_list[0].metadata.name,
                namespace=self.namespace,
            )

        # only get the new log since previous result
        new_log = log.split("\n")
        new_log = new_log[self.log_length :]
        self.log_length += len(new_log)

        return new_log

    def collect_events(self) -> dict:
        """Queries events in the test namespace"""
        events = self.core_v1_api.list_namespaced_event(
            self.namespace, watch=False, pretty=True
        )
        return events.to_dict()

    def collect_not_ready_pods_logs(self) -> Optional[dict[str, list[str]]]:
        """Queries logs of not ready pods in the test namespace"""
        ret = {}
        pods: list[kubernetes_models.V1Pod] = (
            self.core_v1_api.list_namespaced_pod(self.namespace)
        ).items
        for pod in pods:

            # Check if the pod is ready, if not, get the logs
            for condition in pod.status.conditions:
                if condition.type == "Ready" and condition.status != "True":
                    break
                if (
                    condition.type == "Initialized"
                    and condition.status != "True"
                ):
                    break
                if (
                    condition.type == "ContainersReady"
                    and condition.status != "True"
                ):
                    break
            else:
                continue

            for container_statuses in [
                pod.status.container_statuses or [],
                pod.status.init_container_statuses or [],
            ]:
                for container_status in container_statuses:
                    try:
                        log = self.core_v1_api.read_namespaced_pod_log(
                            pod.metadata.name,
                            self.namespace,
                            container=container_status.name,
                        )
                        ret[f"{pod.metadata.name}-{container_status.name}"] = (
                            log.splitlines()
                        )
                    except kubernetes.client.rest.ApiException as e:
                        logger = get_thread_logger(with_prefix=True)
                        logger.error(
                            "Failed to get crash log of pod %s",
                            pod.metadata.name,
                            exc_info=e,
                        )

                    try:
                        if container_status.last_state.terminated is not None:
                            log = self.core_v1_api.read_namespaced_pod_log(
                                pod.metadata.name,
                                self.namespace,
                                container=container_status.name,
                                previous=True,
                            )
                            ret[
                                f"{pod.metadata.name}-{container_status.name}-previous"
                            ] = log.splitlines()
                    except kubernetes.client.rest.ApiException as e:
                        logger = get_thread_logger(with_prefix=True)
                        logger.error(
                            "Failed to get previous log of pod %s",
                            pod.metadata.name,
                            exc_info=e,
                        )
        if len(ret) > 0:
            return ret
        else:
            return None

    def collect_cli_result(self, p: subprocess.CompletedProcess):
        """Collects the result of the kubectl command"""
        cli_output = {}
        cli_output["stdout"] = p.stdout.strip()
        cli_output["stderr"] = p.stderr.strip()
        return cli_output

    def __get_all_objects(self, method) -> dict:
        """Get resources in the application namespace

        Args:
            method: function pointer for getting the object

        Returns
            resource in dict
        """
        result_dict = {}
        resource_objects = method(namespace=self.namespace, watch=False).items

        for obj in resource_objects:
            result_dict[obj.metadata.name] = obj.to_dict()
        return result_dict

    def __get_custom_resources(
        self, namespace: str, group: str, version: str, plural: str
    ) -> dict:
        """Get custom resource object

        Args:
            namespace: namespace of the cr
            group: API group of the cr
            version: version of the cr
            plural: plural name of the cr

        Returns:
            custom resouce object
        """
        result_dict = {}
        custom_resources = self.custom_object_api.list_namespaced_custom_object(
            group, version, namespace, plural
        )["items"]
        for cr in custom_resources:
            result_dict[cr["metadata"]["name"]] = cr
        return result_dict

    def wait_for_system_converge(self, hard_timeout=480) -> bool:
        """This function blocks until the system converges. It keeps
           watching for incoming events. If there is no event within
           60 seconds, the system is considered to have converged.

        Args:
            hard_timeout: the maximal wait time for system convergence

        Returns:
            True if the system fails to converge within the hard timeout
        """
        logger = get_thread_logger(with_prefix=True)

        start_timestamp = time.time()
        logger.info("Waiting for system to converge... ")

        event_stream = self.core_v1_api.list_namespaced_event(
            self.namespace, _preload_content=False, watch=True
        )

        combined_event_queue = self.mp_ctx.Queue(maxsize=0)
        timer_hard_timeout = acto_timer.ActoTimer(
            hard_timeout, combined_event_queue, "timeout"
        )
        watch_process = self.mp_ctx.Process(
            target=self.watch_system_events,
            args=(event_stream, combined_event_queue),
        )

        timer_hard_timeout.start()
        watch_process.start()

        converge = True
        while True:
            try:
                event = combined_event_queue.get(timeout=self.wait_time)
                if event == "timeout":
                    converge = False
                    break
            except queue.Empty:
                ready = True
                statefulsets = self.__get_all_objects(
                    self.app_v1_api.list_namespaced_stateful_set
                )
                deployments = self.__get_all_objects(
                    self.app_v1_api.list_namespaced_deployment
                )
                daemonsets = self.__get_all_objects(
                    self.app_v1_api.list_namespaced_daemon_set
                )

                for sfs in statefulsets.values():
                    if (
                        sfs["status"]["ready_replicas"] is None
                        and sfs["status"]["replicas"] == 0
                    ):
                        # replicas could be 0
                        continue
                    if (
                        sfs["status"]["replicas"]
                        != sfs["status"]["ready_replicas"]
                    ):
                        ready = False
                        logger.info(
                            "Statefulset %s is not ready yet",
                            sfs["metadata"]["name"],
                        )
                        break
                    if sfs["spec"]["replicas"] != sfs["status"]["replicas"]:
                        ready = False
                        logger.info(
                            "Statefulset %s is not ready yet",
                            sfs["metadata"]["name"],
                        )
                        break

                for dp in deployments.values():
                    if dp["spec"]["replicas"] == 0:
                        continue

                    if (
                        dp["status"]["replicas"]
                        != dp["status"]["ready_replicas"]
                    ):
                        ready = False
                        logger.info(
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
                            logger.info(
                                "Deployment %s is not ready yet",
                                dp["metadata"]["name"],
                            )
                            break

                        if (
                            condition["type"] == "Progressing"
                            and condition["status"] != "True"
                        ):
                            ready = False
                            logger.info(
                                "Deployment %s is not ready yet",
                                dp["metadata"]["name"],
                            )
                            break

                for ds in daemonsets.values():
                    if (
                        ds["status"]["number_ready"]
                        != ds["status"]["current_number_scheduled"]
                    ):
                        ready = False
                        logger.info(
                            "Daemonset %s is not ready yet",
                            ds["metadata"]["name"],
                        )
                        break
                    if (
                        ds["status"]["desired_number_scheduled"]
                        != ds["status"]["number_ready"]
                    ):
                        ready = False
                        logger.info(
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
                        logger.info(
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
            logger.info("System took %s to converge", time_elapsed)
            return False
        else:
            logger.error(
                "System failed to converge within %d seconds", hard_timeout
            )
            return True

    def watch_system_events(self, event_stream, q: multiprocessing.Queue):
        """A process that watches namespaced events"""
        for _ in event_stream:
            try:
                q.put("event")
            except (ValueError, AssertionError):
                pass


def decode_secret_data(secrets: dict) -> dict:
    """Decodes secret's b64-encrypted data in the secret object"""
    logger = get_thread_logger(with_prefix=True)
    for secret in secrets:
        try:
            if (
                "data" in secrets[secret]
                and secrets[secret]["data"] is not None
            ):
                for key in secrets[secret]["data"]:
                    secrets[secret]["data"][key] = base64.b64decode(
                        secrets[secret]["data"][key]
                    ).decode("utf-8")
        except UnicodeDecodeError as e:
            # skip secret if decoding fails
            logger.error(e)
    return secrets


def group_pods(all_pods: dict) -> tuple[dict, dict, dict]:
    """Groups pods into deployment pods, daemonset pods, and other pods

    For deployment pods, they are further grouped by their owner reference

    Return:
        Tuple of (deployment_pods, daemonset_pods, other_pods)
    """
    deployment_pods = {}
    daemonset_pods = {}
    other_pods = {}
    for name, pod in all_pods.items():
        if (
            "acto/tag" in pod["metadata"]["labels"]
            and pod["metadata"]["labels"]["acto/tag"] == "custom-oracle"
        ):
            # skip pods spawned by users' custom oracle
            continue

        if pod["metadata"]["owner_references"] is not None:
            owner_reference = pod["metadata"]["owner_references"][0]
            if (
                owner_reference["kind"] == "ReplicaSet"
                or owner_reference["kind"] == "Deployment"
            ):
                owner_name = owner_reference["name"]
                if owner_reference["kind"] == "ReplicaSet":
                    # chop off the suffix of the ReplicaSet name
                    # to get the deployment name
                    owner_name = "-".join(owner_name.split("-")[:-1])
                if owner_name not in deployment_pods:
                    deployment_pods[owner_name] = [pod]
                else:
                    deployment_pods[owner_name].append(pod)
            elif owner_reference["kind"] == "DaemonSet":
                owner_name = owner_reference["name"]
                if owner_name not in daemonset_pods:
                    daemonset_pods[owner_name] = [pod]
                else:
                    daemonset_pods[owner_name].append(pod)
            else:
                other_pods[name] = pod
        else:
            other_pods[name] = pod

    return deployment_pods, daemonset_pods, other_pods
