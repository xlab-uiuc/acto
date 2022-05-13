from kubernetes.client.models import V1Deployment, V1StatefulSet, V1Namespace, V1ObjectMeta
import kubernetes
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


def create_namespace(apiclient, name: str) -> V1Namespace:
    corev1Api = kubernetes.client.CoreV1Api(apiclient)
    namespace = corev1Api.create_namespace(
        V1Namespace(metadata=V1ObjectMeta(name=name)))
    return namespace