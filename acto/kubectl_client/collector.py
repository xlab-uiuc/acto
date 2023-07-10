import base64
import json
from typing import Optional, Dict

import kubernetes

from acto.common import *
from acto.kubectl_client import KubectlClient
from acto.lib.dict import visit_dict
from acto.snapshot import PodLog
from acto.utils import get_thread_logger


class Collector:

    def __init__(self, namespace: str, kubectl_client: KubectlClient, crd_meta_info=None):
        self.namespace = namespace
        self.crd_meta_info: Optional[dict] = crd_meta_info
        self.log_length = 0

        apiclient = kubectl_client.api_client
        self.coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        self.appV1Api = kubernetes.client.AppsV1Api(apiclient)
        self.batchV1Api = kubernetes.client.BatchV1Api(apiclient)
        self.customObjectApi = kubernetes.client.CustomObjectsApi(apiclient)
        self.policyV1Api = kubernetes.client.PolicyV1Api(apiclient)
        self.networkingV1Api = kubernetes.client.NetworkingV1Api(apiclient)
        self.rbacAuthorizationV1Api = kubernetes.client.RbacAuthorizationV1Api(apiclient)
        self.storageV1Api = kubernetes.client.StorageV1Api(apiclient)
        self.schedulingV1Api = kubernetes.client.SchedulingV1Api(apiclient)
        self.resource_methods = {
            'pod': self.coreV1Api.list_namespaced_pod,
            'stateful_set': self.appV1Api.list_namespaced_stateful_set,
            'deployment': self.appV1Api.list_namespaced_deployment,
            'config_map': self.coreV1Api.list_namespaced_config_map,
            'service': self.coreV1Api.list_namespaced_service,
            'pvc': self.coreV1Api.list_namespaced_persistent_volume_claim,
            'cronjob': self.batchV1Api.list_namespaced_cron_job,
            'ingress': self.networkingV1Api.list_namespaced_ingress,
            'network_policy': self.networkingV1Api.list_namespaced_network_policy,
            'pod_disruption_budget': self.policyV1Api.list_namespaced_pod_disruption_budget,
            'secret': self.coreV1Api.list_namespaced_secret,
            'endpoints': self.coreV1Api.list_namespaced_endpoints,
            'service_account': self.coreV1Api.list_namespaced_service_account,
            'job': self.batchV1Api.list_namespaced_job,
            'role': self.rbacAuthorizationV1Api.list_namespaced_role,
            'role_binding': self.rbacAuthorizationV1Api.list_namespaced_role_binding,
        }

    def collect_system_state(self) -> dict:
        """
        Queries resources in the test namespace, computes delta and returns the system state.
        """
        resources = {}

        for resource, method in self.resource_methods.items():
            resources[resource] = self.__get_all_objects(method)
            if resource == 'pod':
                # put pods managed by deployment / replicasets into an array
                all_pods = self.__get_all_objects(method)
                resources['deployment_pods'], resources['pod'] = group_pods(all_pods)
            elif resource == 'secret':
                resources[resource] = decode_secret_data(resources[resource])

        # if crd is not specified, do not collect custom resource
        if not self.crd_meta_info:
            return resources

        current_cr = self.__get_custom_resources(self.namespace, self.crd_meta_info['group'],
                                                 self.crd_meta_info['version'],
                                                 self.crd_meta_info['plural'])

        resources['custom_resource_spec'] = current_cr['test-cluster']['spec'] \
            if 'spec' in current_cr['test-cluster'] else None
        resources['custom_resource_status'] = current_cr['test-cluster']['status'] \
            if 'status' in current_cr['test-cluster'] else None

        return resources

    def collect_operator_log(self) -> List[str]:
        """
        Queries operator log in the test namespace, computes delta and returns the system state.
        Args:
        """
        logger = get_thread_logger(with_prefix=True)

        operator_pod_list = self.coreV1Api.list_namespaced_pod(
            namespace=self.namespace, watch=False, label_selector="acto/tag=operator-pod").items

        if len(operator_pod_list) >= 1:
            logger.debug('Got operator pod: pod name:' + operator_pod_list[0].metadata.name)
        else:
            logger.error('Failed to find operator pod')
            # TODO: refine what should be done if no operator pod can be found
            return []

        log = self.coreV1Api.read_namespaced_pod_log(name=operator_pod_list[0].metadata.name,
                                                     namespace=self.namespace)

        # only get the new log since previous result
        new_log = log.strip().split('\n')
        new_log = new_log[self.log_length:]
        self.log_length += len(new_log)

        return new_log

    def collect_events(self) -> dict:
        events = self.coreV1Api.list_namespaced_event(self.namespace,
                                                      pretty=True,
                                                      _preload_content=False)

        return json.loads(events.data)

    def collect_not_ready_pods_logs(self) -> Dict[str, PodLog]:
        logs = {}
        pods = self.coreV1Api.list_namespaced_pod(self.namespace)
        for pod in pods.items:
            for container_statuses in [pod.status.container_statuses or [], pod.status.init_container_statuses or []]:
                for container_status in container_statuses:
                    if not container_status.ready:
                        log = self.coreV1Api.read_namespaced_pod_log(pod.metadata.name, self.namespace,
                                                                     container=container_status.name)
                        log = log.strip().split('\n')

                        log_prev = self.coreV1Api.read_namespaced_pod_log(pod.metadata.name, self.namespace,
                                                                          container=container_status.name, previous=True)
                        log_prev = log_prev.strip().split('\n')

                        logs[pod.metadata.name] = PodLog(log=log, previous_log=log_prev)

        return logs

    def __get_all_objects(self, method) -> dict:
        """
        Get resources in the application namespace

        Args:
            method: function pointer for getting the object

        Returns
            resource in dict
        """
        result_dict = {}
        resource_objects = method(namespace=self.namespace, watch=False).items

        for resource_object in resource_objects:
            result_dict[resource_object.metadata.name] = resource_object.to_dict()
        return result_dict

    def __get_custom_resources(self, namespace: str, group: str, version: str, plural: str) -> dict:
        """
        Get custom resource object

        Args:
            namespace: namespace of the cr
            group: API group of the cr
            version: version of the cr
            plural: plural name of the cr

        Returns:
            custom resource object
        """
        result_dict = {}
        custom_resources = self.customObjectApi.list_namespaced_custom_object(group, version, namespace, plural)['items']
        for cr in custom_resources:
            result_dict[cr['metadata']['name']] = cr
        return result_dict


def decode_secret_data(secrets: dict) -> dict:
    """
    Decodes secret's b64-encrypted data in the secret object
    """
    logger = get_thread_logger(with_prefix=True)
    for secret in secrets:
        (exists, data) = visit_dict(secrets[secret], ['data'])
        if exists:
            for key in data:
                try:
                    data[key] = base64.b64decode(data[key]).decode('utf-8')
                except Exception as e:
                    # skip secret if decoding fails
                    logger.error(f'Failed to decode the secret {secret}.{key}: {e}')
    return secrets


def group_pods(all_pods: dict) -> Tuple[dict, dict]:
    """
    Groups pods into deployment pods and other pods

    For deployment pods, they are further grouped by their owner reference

    Return:
        Tuple of (deployment_pods, other_pods)
    """
    deployment_pods = {}
    other_pods = {}
    for name, pod in all_pods.items():
        if 'acto/tag' in pod['metadata']['labels'] and pod['metadata']['labels']['acto/tag'] == 'custom-oracle':
            # skip pods spawned by users' custom oracle
            continue
        elif pod['metadata']['owner_references'] is not None:
            owner_reference = pod['metadata']['owner_references'][0]
            if owner_reference['kind'] == 'ReplicaSet' or owner_reference['kind'] == 'Deployment':
                owner_name = owner_reference['name']
                if owner_reference['kind'] == 'ReplicaSet':
                    # chop off the suffix of the ReplicaSet name to get the deployment name
                    owner_name = '-'.join(owner_name.split('-')[:-1])
                if owner_name not in deployment_pods:
                    deployment_pods[owner_name] = [pod]
                else:
                    deployment_pods[owner_name].append(pod)
            else:
                other_pods[name] = pod
        else:
            other_pods[name] = pod

    return deployment_pods, other_pods
