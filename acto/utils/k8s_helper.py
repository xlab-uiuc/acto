import time
from typing import Optional

import kubernetes
import yaml
from kubernetes.client.models import (
    V1Deployment,
    V1Namespace,
    V1ObjectMeta,
    V1Pod,
    V1StatefulSet,
)

from .thread_logger import get_thread_logger


def is_pod_ready(pod: V1Pod) -> bool:
    """Check if the pod is ready

    Args:
        pod: Pod object in kubernetes

    Returns:
        if the pod is ready
    """
    if pod.status is None or pod.status.conditions is None:
        return False

    for condition in pod.status.conditions:
        if condition.type == "Ready" and condition.status == "True":
            return True
    return False


def get_deployment_available_status(deployment: V1Deployment) -> bool:
    """Get availability status from deployment condition

    Args:
        deployment: Deployment object in kubernetes

    Returns:
        if the deployment is available
    """
    if deployment.status is None or deployment.status.conditions is None:
        return False

    for condition in deployment.status.conditions:
        if condition.type == "Available" and condition.status == "True":
            return True
    return False


def get_stateful_set_available_status(stateful_set: V1StatefulSet) -> bool:
    """Get availability status from stateful set condition

    Args:
        stateful_set: stateful set object in kubernetes

    Returns:
        if the stateful set is available
    """
    if stateful_set.status is None:
        return False
    if (
        stateful_set.status.replicas > 0
        and stateful_set.status.current_replicas == stateful_set.status.replicas
    ):
        return True
    return False


def get_yaml_existing_namespace(fn: str) -> Optional[str]:
    """Get yaml's existing namespace

    Args:
        fn (str): Yaml file path

    Returns:
        bool: True if yaml has namespace
    """
    with open(fn, "r", encoding="utf-8") as operator_yaml:
        parsed_operator_documents = yaml.load_all(
            operator_yaml, Loader=yaml.FullLoader
        )
        for document in parsed_operator_documents:
            if (
                document is not None
                and "metadata" in document
                and "namespace" in document["metadata"]
            ):
                return document["metadata"]["namespace"]
    return None


def get_deployment_name_from_yaml(fn: str) -> Optional[str]:
    """Get deployment name from yaml file"""
    with open(fn, "r", encoding="utf-8") as operator_yaml:
        parsed_operator_documents = yaml.load_all(
            operator_yaml, Loader=yaml.FullLoader
        )
        for document in parsed_operator_documents:
            if (
                document is not None
                and "kind" in document
                and document["kind"] == "Deployment"
            ):
                return document["metadata"]["name"]
    return None


def create_namespace(apiclient, name: str) -> V1Namespace:
    """Create a namespace in kubernetes"""
    corev1_api = kubernetes.client.CoreV1Api(apiclient)
    namespace = None
    try:
        namespace = corev1Api.create_namespace(
            V1Namespace(metadata=V1ObjectMeta(name=name))
        )
    except Exception as e:
        logger.error(e)
    return namespace


def delete_namespace(apiclient, name: str) -> bool:
    """Delete a namespace in kubernetes"""
    corev1_api = kubernetes.client.CoreV1Api(apiclient)
    corev1_api.delete_namespace(name=name)
    return True


def delete_operator_pod(apiclient, namespace: str) -> bool:
    """Delete the operator pod in kubernetes"""
    logger = get_thread_logger(with_prefix=False)

    corev1_api = kubernetes.client.CoreV1Api(apiclient)

    operator_pod_list = corev1_api.list_namespaced_pod(
        namespace=namespace, watch=False, label_selector="acto/tag=operator-pod"
    ).items

    if len(operator_pod_list) >= 1:
        logger.debug(
            "Got operator pod: pod name: %s", operator_pod_list[0].metadata.name
        )
    else:
        logger.error("Failed to find operator pod")
        return False
        # TODO: refine what should be done if no operator pod can be found

    pod = corev1_api.delete_namespaced_pod(
        name=operator_pod_list[0].metadata.name, namespace=namespace
    )
    if pod is None:
        return False
    else:
        time.sleep(10)
        return True
