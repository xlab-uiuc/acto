import logging
from kubernetes.client.models import V1Deployment, V1StatefulSet, V1Namespace, V1ObjectMeta
import kubernetes
from typing import List, Optional, Tuple
import yaml
from constant import CONST
import time

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
            if document != None and 'metadata' in document and 'namespace' in document['metadata']:
                return document['metadata']['namespace']
    return None


def create_namespace(apiclient, name: str) -> V1Namespace:
    corev1Api = kubernetes.client.CoreV1Api(apiclient)
    namespace = None
    try:
        namespace = corev1Api.create_namespace(
            V1Namespace(metadata=V1ObjectMeta(name=name)))
    except Exception as e:
                logging.error(e)
    return namespace

def delete_operator_pod(apiclient, namespace: str) -> bool:
    coreV1Api = kubernetes.client.CoreV1Api(apiclient)

    operator_pod_list = coreV1Api.list_namespaced_pod(
        namespace=namespace, watch=False, label_selector="acto/tag=operator-pod").items

    if len(operator_pod_list) >= 1:
        logging.debug('Got operator pod: pod name:' + operator_pod_list[0].metadata.name)
    else:
        logging.error('Failed to find operator pod')
        return False
        #TODO: refine what should be done if no operator pod can be found

    pod = coreV1Api.delete_namespaced_pod(name=operator_pod_list[0].metadata.name,
                                                     namespace=namespace)
    if pod == None:
        return False
    else:
        time.sleep(10)
        return True