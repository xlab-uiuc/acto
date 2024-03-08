import time

import kubernetes
import yaml

import acto.utils as utils
from acto.common import *
from acto.kubectl_client.kubectl import KubectlClient
from acto.lib.operator_config import DELEGATED_NAMESPACE, DeployConfig
from acto.utils import get_thread_logger
from acto.utils.preprocess import add_acto_label


def wait_for_pod_ready(apiclient: kubernetes.client.ApiClient):
    logger = get_thread_logger(with_prefix=True)
    logger.debug("Waiting for all pods to be ready")
    time.sleep(5)
    pod_ready = False
    for tick in range(600):
        # check if all pods are ready
        pods = kubernetes.client.CoreV1Api(
            apiclient).list_pod_for_all_namespaces().items

        all_pods_ready = True
        for pod in pods:
            if pod.status.phase == "Succeeded":
                continue
            if not utils.is_pod_ready(pod):
                all_pods_ready = False

        if all_pods_ready:
            logger.info("Operator ready")
            pod_ready = True
            break
        time.sleep(5)
    logger.info("All pods took %d seconds to get ready" % (tick * 5))
    if not pod_ready:
        logger.error("Some pods failed to be ready within timeout")
        return False
    else:
        return True


class Deploy():

    def __init__(self, deploy_config: DeployConfig) -> None:
        self._deploy_config = deploy_config
        print(deploy_config)

        self._operator_yaml: str = None
        for step in self._deploy_config.steps:
            if step.apply and step.apply.operator:
                self._operator_yaml = step.apply.file
                break
        else:
            raise Exception("No operator yaml found in deploy config")
        
        # Extract the operator_container_name from config
        self._operator_container_name = None
        for step in self._deploy_config.steps:
            if step.apply and step.apply.operator:
                self._operator_container_name = step.apply.operator_container_name
                break

    @property
    def operator_yaml(self) -> str:
        return self._operator_yaml

    def deploy(self,
               kubeconfig: str,
               context_name: str,
               kubectl_client: KubectlClient,
               namespace: str):
        logger = get_thread_logger(with_prefix=True)
        print_event("Deploying operator...")
        api_client = kubernetes_client(kubeconfig, context_name)

        ret = utils.create_namespace(api_client, namespace)
        if ret is None:
            logger.error("Failed to create namespace")

        # Run the steps in the deploy config one by one
        for step in self._deploy_config.steps:
            if step.apply:
                # args = ["apply", "--server-side", "-f", step.apply.file,
                #         "--context", context_name]
                args = ["apply", "-f", step.apply.file,
                        "--context", context_name]

                # Use the namespace from the argument if the namespace is delegated
                # If the namespace from the config is explicitly specified,
                # use the specified namespace
                # If the namespace from the config is set to None, do not apply
                # with namespace
                if step.apply.namespace == DELEGATED_NAMESPACE:
                    args += ["-n", namespace]
                elif step.apply.namespace is not None:
                    args += ["-n", step.apply.namespace]

                # Apply the yaml file and then wait for the pod to be ready
                p = kubectl_client.kubectl(args, capture_output=True)
                if p.returncode != 0:
                    logger.error(
                        "Failed to deploy operator due to error from kubectl" +
                        f" (returncode={p.returncode})" +
                        f" (stdout={p.stdout})" +
                        f" (stderr={p.stderr})")
                    return False
                elif not wait_for_pod_ready(api_client):
                    logger.error(
                        "Failed to deploy operator due to timeout waiting for pod to be ready")
                    return False
            elif step.wait:
                # Simply wait for the specified duration
                time.sleep(step.wait.duration)
            elif step.create:
                args = ["create", "-f", step.create.file,
                        "--context", context_name]

                # Use the namespace from the argument if the namespace is delegated
                # If the namespace from the config is explicitly specified,
                # use the specified namespace
                # If the namespace from the config is set to None, do not apply
                # with namespace
                if step.create.namespace == DELEGATED_NAMESPACE:
                    args += ["-n", namespace]
                elif step.create.namespace is not None:
                    args += ["-n", step.create.namespace]

                # Apply the yaml file and then wait for the pod to be ready
                p = kubectl_client.kubectl(args)
                if p.returncode != 0:
                    logger.error(
                        "Failed to deploy operator due to error from kubectl" +
                        f" (returncode={p.returncode})" +
                        f" (stdout={p.stdout})" +
                        f" (stderr={p.stderr})")
                    return False

        # Add acto label to the operator pod
        add_acto_label(api_client, namespace)
        if not wait_for_pod_ready(api_client):
            logger.error("Failed to deploy operator")
            return False

        time.sleep(20)

        print_event("Operator deployed")
        return True

    def deploy_with_retry(self,
                          kubeconfig: str,
                          context_name: str,
                          kubectl_client: KubectlClient,
                          namespace: str,
                          retry_count: int = 3):
        logger = get_thread_logger(with_prefix=True)
        for i in range(retry_count):
            if self.deploy(kubeconfig, context_name, kubectl_client, namespace):
                return True
            else:
                logger.error("Failed to deploy operator, retrying...")
        return False

    def operator_name(self) -> str:
        with open(self._operator_yaml) as f:
            operator_yamls = yaml.load_all(f, Loader=yaml.FullLoader)
            for yaml_ in operator_yamls:
                if yaml_["kind"] == "Deployment":
                    return yaml_["metadata"]["name"]
        return None

    @property
    def operator_container_name(self) -> str:
        return self._operator_container_name
