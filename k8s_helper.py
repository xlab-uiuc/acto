import tempfile
from kubernetes.client.models import V1Deployment, V1StatefulSet
import kubernetes.client
from typing import List, Optional, Tuple
import yaml
from constant import CONST

CONST = CONST()


def get_deployment_available_status(deployment: V1Deployment) -> bool:
    '''Get availability status from deployment condition

    Args:
        deployment: Deployment object in kubernetes

    Returns:
        if the deployment is available
    '''
    if deployment.status is None or deployment.status.conditions is None:
        return False

    for condition in deployment.status.conditions:
        if condition.type == 'Available' and condition.status == 'True':
            return True
    return False


def get_stateful_set_available_status(stateful_set: V1StatefulSet) -> bool:
    '''Get availability status from stateful set condition

    Args:
        stateful_set: stateful set object in kubernetes

    Returns:
        if the stateful set is available
    '''
    if stateful_set.status is None:
        return False
    if stateful_set.status.replicas > 0 and stateful_set.status.current_replicas == stateful_set.status.replicas:
        return True
    return False


def get_namespaced_resources() -> Tuple[List[str], List[str]]:
    '''Get namespaced and non-namespaced available resources list

    Returns:
        list of namespaced kind and list of non-namespaced kind
    '''
    namespaced_resources = []
    non_namespaced_resources = []
    appv1Api = kubernetes.client.AppsV1Api()
    for resource in appv1Api.get_api_resources().resources:
        if resource.namespaced:
            namespaced_resources.append(resource.kind)
        else:
            non_namespaced_resources.append(resource.kind)
    return namespaced_resources, non_namespaced_resources


def override_namespace(fn: str) -> str:
    """_summary_

    Args:
        fn (str): Yaml file path

    Returns:
        str: New yaml file path with overridden namespace
    """
    namespaced_resources, _ = get_namespaced_resources()
    new_document_list = []
    with open(fn, 'r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if document['kind'] in namespaced_resources:
                document['metadata']['namespace'] = CONST.ACTO_NAMESPACE
            if 'subjects' in document:
                for subject in document['subjects']:
                    subject['namespace'] = CONST.ACTO_NAMESPACE
            new_document_list.append(document)
    new_yaml = tempfile.mkstemp()[1]
    with open(new_yaml, 'w') as f:
        yaml.dump_all(new_document_list, f)
    return new_yaml


def get_yaml_existing_namespace(fn: str) -> Optional[str]:
    '''Get yaml's existing namespace

    Args:
        fn (str): Yaml file path

    Returns:
        bool: True if yaml has namespace
    '''
    with open(fn, 'r') as operator_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        for document in parsed_operator_documents:
            if 'metadata' in document and 'namespace' in document['metadata']:
                return document['metadata']['namespace']
    return None


def create_namespace(name: str) -> kubernetes.client.V1Namespace:
    corev1Api = kubernetes.client.CoreV1Api()
    namespace = corev1Api.create_namespace(
        kubernetes.client.V1Namespace(metadata=kubernetes.client.V1ObjectMeta(
            name=name)))
    return namespace