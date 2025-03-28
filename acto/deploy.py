import logging
import subprocess
import time
from typing import Optional

from acto import utils
from acto.common import kubernetes_client, print_event
from acto.kubectl_client.helm import Helm
from acto.kubectl_client.kubectl import KubectlClient
from acto.lib.operator_config import DELEGATED_NAMESPACE, DeployConfig
from acto.utils import get_thread_logger
from acto.utils.k8s_helper import (
    get_deployment_name_from_yaml,
    get_yaml_existing_namespace,
)
from acto.utils.preprocess import add_acto_label


def wait_for_pod_ready(kubectl_client: KubectlClient) -> bool:
    """Wait for all pods to be ready"""
    now = time.time()
    try:
        i = 0
        while i < 3:
            p = kubectl_client.wait_for_all_pods(timeout=600)
            if p.returncode == 0:
                break
            i += 1
    except subprocess.TimeoutExpired:
        logging.error("Timeout waiting for all pods to be ready")
        return False
    if p.returncode != 0:
        logging.error(
            "Failed to wait for all pods to be ready due to error from kubectl"
            + f" (returncode={p.returncode})"
            + f" (stdout={p.stdout})"
            + f" (stderr={p.stderr})"
        )
        return False
    logging.info(
        "Waited for all pods to be ready for %d seconds", time.time() - now
    )
    return True


class Deploy:
    """Deploy the operator using the deploy config"""

    def __init__(self, deploy_config: DeployConfig) -> None:
        self._deploy_config = deploy_config

        self._operator_existing_namespace: Optional[str] = None
        for step in self._deploy_config.steps:
            if step.apply and step.apply.operator:
                self._operator_existing_namespace = get_yaml_existing_namespace(
                    step.apply.file
                )
                break
            if step.helm_install and step.helm_install.operator:
                self._operator_existing_namespace = None
                break

        # Extract the operator_container_name from config
        self._operator_container_name = None
        for step in self._deploy_config.steps:
            if step.apply and step.apply.operator:
                self._operator_container_name = (
                    step.apply.operator_container_name
                )
                break
            if step.helm_install and step.helm_install.operator:
                self._operator_container_name = (
                    step.helm_install.operator_container_name
                )
                break

        self._operator_deployment_name = None
        for step in self._deploy_config.steps:
            if step.apply and step.apply.operator:
                if (
                    ret := get_deployment_name_from_yaml(step.apply.file)
                ) is not None:
                    self._operator_deployment_name = ret
                    break
            if step.helm_install and step.helm_install.operator:
                self._operator_deployment_name = (
                    step.helm_install.operator_deployment_name
                )
                break

    @property
    def operator_existing_namespace(self) -> Optional[str]:
        """Get the operator yaml file path"""
        return self._operator_existing_namespace

    def deploy(
        self,
        kubeconfig: str,
        context_name: str,
        kubectl_client: KubectlClient,
        namespace: str,
    ):
        """Deploy the operator using the deploy config"""
        logger = get_thread_logger(with_prefix=True)
        print_event("Deploying operator...")
        api_client = kubernetes_client(kubeconfig, context_name)

        ret = utils.create_namespace(api_client, namespace)
        if ret is None:
            logger.error("Failed to create namespace")

        # Run the steps in the deploy config one by one
        for step in self._deploy_config.steps:
            if step.apply:
                args = ["apply", "--server-side", "-f", step.apply.file]

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
                        "Failed to deploy operator due to error from kubectl"
                        + f" (returncode={p.returncode})"
                        + f" (stdout={p.stdout})"
                        + f" (stderr={p.stderr})"
                    )
                    return False
                elif not wait_for_pod_ready(kubectl_client):
                    logger.error(
                        "Failed to deploy operator due to timeout waiting for pod to be ready"
                    )
                    return False
            elif step.wait:
                # Simply wait for the specified duration
                time.sleep(step.wait.duration)
            elif step.helm_install:
                # Use the namespace from the argument if the namespace is delegated
                # If the namespace from the config is explicitly specified,
                # use the specified namespace
                # If the namespace from the config is set to None, do not apply
                # with namespace
                release_namespace = "default"
                if step.helm_install.namespace == DELEGATED_NAMESPACE:
                    release_namespace = namespace
                elif step.helm_install.namespace is not None:
                    release_namespace = step.helm_install.namespace

                # Install the helm chart
                helm = Helm(kubeconfig, context_name)
                p = helm.install(
                    release_name=step.helm_install.release_name,
                    chart=step.helm_install.chart,
                    namespace=release_namespace,
                    repo=step.helm_install.repo,
                    version=step.helm_install.version,
                )
                if p.returncode != 0:
                    logger.error(
                        "Failed to deploy operator due to error from helm"
                        + f" (returncode={p.returncode})"
                        + f" (stdout={p.stdout})"
                        + f" (stderr={p.stderr})"
                    )
                    return False

        # Add acto label to the operator pod
        add_acto_label(api_client, namespace)
        if not wait_for_pod_ready(kubectl_client):
            logger.error("Failed to deploy operator")
            return False

        time.sleep(20)

        print_event("Operator deployed")
        return True

    def deploy_with_retry(
        self,
        kubeconfig: str,
        context_name: str,
        kubectl_client: KubectlClient,
        namespace: str,
        retry_count: int = 3,
    ):
        """Deploy the operator with retry"""
        logger = get_thread_logger(with_prefix=True)
        for _ in range(retry_count):
            if self.deploy(kubeconfig, context_name, kubectl_client, namespace):
                return True
            else:
                logger.error("Failed to deploy operator, retrying...")
        return False

    def operator_name(self) -> Optional[str]:
        """Get the name of the operator deployment"""
        return self._operator_deployment_name

    @property
    def operator_container_name(self) -> Optional[str]:
        """Get the name of the operator container"""
        return self._operator_container_name
