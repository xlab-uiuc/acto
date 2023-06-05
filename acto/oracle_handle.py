from typing import List

import kubernetes
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_stateful_set import V1StatefulSet

from acto.kubectl_client import KubectlClient
from acto.snapshot import Snapshot


class OracleHandle:

    def __init__(self, kubectl_client: KubectlClient, k8s_client: kubernetes.client.ApiClient,
                 namespace: str, snapshots: List[Snapshot]):
        self.kubectl_client = kubectl_client
        self.k8s_client = k8s_client
        self.namespace = namespace
        self.snapshots = snapshots

    def get_stateful_sets(self) -> List[V1StatefulSet]:
        '''Get all stateful sets in the namespace
        
        Returns:
            list[V1StatefulSet]
        '''
        appv1 = kubernetes.client.AppsV1Api(self.k8s_client)
        return appv1.list_namespaced_stateful_set(self.namespace).items

    def get_pods_in_stateful_set(self, stateful_set: V1StatefulSet) -> List[V1Pod]:
        '''Get all pods in the stateful set
        
        Args:
            stateful_set: stateful set object in kubernetes
        
        Returns:
            list[V1Pod]
        '''

        all_pods: List[V1Pod] = kubernetes.client.CoreV1Api(self.k8s_client).list_namespaced_pod(
            self.namespace).items

        for pod in all_pods:
            if pod.metadata.owner_references != None:
                for reference in pod.metadata.owner_references:
                    if reference.uid == stateful_set.metadata.uid:
                        yield pod

    def get_cr(self) -> dict:
        '''Get the most recent applied CR
        
        Returns:
            dict
        '''
        return self.snapshots[-1].input