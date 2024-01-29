"""Kubernetes system state model"""

import json

import kubernetes
import pydantic
from typing_extensions import Self

from acto.serialization import ActoEncoder
from acto.system_state.cluster_role import ClusterRoleState
from acto.system_state.cluster_role_binding import ClusterRoleBindingState
from acto.system_state.config_map import ConfigMapState
from acto.system_state.cron_job import CronJobState
from acto.system_state.daemon_set import DaemonSetState
from acto.system_state.deployment import DeploymentState
from acto.system_state.endpoints import EndpointsState
from acto.system_state.ingress import IngressState
from acto.system_state.job import JobState
from acto.system_state.kubernetes_object import ObjectDiff
from acto.system_state.network_policy import NetworkPolicyState
from acto.system_state.persistent_volume import PersistentVolumeState
from acto.system_state.persistent_volume_claim import PersistentVolumeClaimState
from acto.system_state.pod import PodState
from acto.system_state.replica_set import ReplicaSetState
from acto.system_state.role import RoleState
from acto.system_state.role_binding import RoleBindingState
from acto.system_state.secret import SecretState
from acto.system_state.service import ServiceState
from acto.system_state.service_account import ServiceAccountState
from acto.system_state.stateful_set import StatefulSetState
from acto.system_state.storage_class import StorageClassState


class KubernetesSystemDiff(pydantic.BaseModel):
    """Kubernetes system diff model"""

    cluster_role_binding: ObjectDiff
    cluster_role: ObjectDiff
    config_map: ObjectDiff
    cron_job: ObjectDiff
    daemon_set: ObjectDiff
    deployment: ObjectDiff
    endpoint: ObjectDiff
    ingress: ObjectDiff
    job: ObjectDiff
    network_policy: ObjectDiff
    persistent_volume_claim: ObjectDiff
    persistent_volume: ObjectDiff
    pod: ObjectDiff
    replica_set: ObjectDiff
    role_binding: ObjectDiff
    role: ObjectDiff
    secret: ObjectDiff
    service_account: ObjectDiff
    service: ObjectDiff
    stateful_set: ObjectDiff
    storage_class: ObjectDiff


class KubernetesSystemHealth(pydantic.BaseModel):
    """Kubernetes system health status model"""

    daemon_set: tuple[bool, str]
    deployment: tuple[bool, str]
    job: tuple[bool, str]
    pod: tuple[bool, str]
    replica_set: tuple[bool, str]
    stateful_set: tuple[bool, str]

    def is_healthy(self) -> bool:
        """Check if Kubernetes system is healthy"""
        return all(
            [
                self.daemon_set[0],
                self.deployment[0],
                self.job[0],
                self.pod[0],
                self.replica_set[0],
                self.stateful_set[0],
            ]
        )

    def __str__(self) -> str:
        ret = ""
        if not self.daemon_set[0]:
            ret += f"DaemonSet: {self.daemon_set[1]}\n"
        if not self.deployment[0]:
            ret += f"Deployment: {self.deployment[1]}\n"
        if not self.job[0]:
            ret += f"Job: {self.job[1]}\n"
        if not self.pod[0]:
            ret += f"Pod: {self.pod[1]}\n"
        if not self.replica_set[0]:
            ret += f"ReplicaSet: {self.replica_set[1]}\n"
        if not self.stateful_set[0]:
            ret += f"StatefulSet: {self.stateful_set[1]}\n"
        return ret


class KubernetesSystemState(pydantic.BaseModel):
    """System state of the cluster, including all Kubernetes resources"""

    cluster_role_binding: ClusterRoleBindingState
    cluster_role: ClusterRoleState
    config_map: ConfigMapState
    cron_job: CronJobState
    daemon_set: DaemonSetState
    deployment: DeploymentState
    endpoint: EndpointsState
    ingress: IngressState
    job: JobState
    network_policy: NetworkPolicyState
    persistent_volume_claim: PersistentVolumeClaimState
    persistent_volume: PersistentVolumeState
    pod: PodState
    replica_set: ReplicaSetState
    role_binding: RoleBindingState
    role: RoleState
    secret: SecretState
    service_account: ServiceAccountState
    service: ServiceState
    stateful_set: StatefulSetState
    storage_class: StorageClassState

    @classmethod
    def from_api_client(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        """Initialize Kubernetes system state by fetching all objects from
        Kubernetes API server.
        """
        return cls(
            cluster_role_binding=ClusterRoleBindingState.from_api_client(
                api_client
            ),
            cluster_role=ClusterRoleState.from_api_client(api_client),
            config_map=ConfigMapState.from_api_client_namespaced(
                api_client, namespace
            ),
            cron_job=CronJobState.from_api_client_namespaced(
                api_client, namespace
            ),
            daemon_set=DaemonSetState.from_api_client_namespaced(
                api_client, namespace
            ),
            deployment=DeploymentState.from_api_client_namespaced(
                api_client, namespace
            ),
            endpoint=EndpointsState.from_api_client_namespaced(
                api_client, namespace
            ),
            ingress=IngressState.from_api_client_namespaced(
                api_client, namespace
            ),
            job=JobState.from_api_client_namespaced(api_client, namespace),
            network_policy=NetworkPolicyState.from_api_client_namespaced(
                api_client, namespace
            ),
            persistent_volume_claim=PersistentVolumeClaimState.from_api_client_namespaced(
                api_client, namespace
            ),
            persistent_volume=PersistentVolumeState.from_api_client(api_client),
            pod=PodState.from_api_client_namespaced(api_client, namespace),
            replica_set=ReplicaSetState.from_api_client_namespaced(
                api_client, namespace
            ),
            role_binding=RoleBindingState.from_api_client_namespaced(
                api_client, namespace
            ),
            role=RoleState.from_api_client_namespaced(api_client, namespace),
            secret=SecretState.from_api_client_namespaced(
                api_client, namespace
            ),
            service_account=ServiceAccountState.from_api_client_namespaced(
                api_client, namespace
            ),
            service=ServiceState.from_api_client_namespaced(
                api_client, namespace
            ),
            stateful_set=StatefulSetState.from_api_client_namespaced(
                api_client, namespace
            ),
            storage_class=StorageClassState.from_api_client(api_client),
        )

    def diff_from(self, other: Self) -> KubernetesSystemDiff:
        """Diff with other Kubernetes system state"""
        return KubernetesSystemDiff(
            cluster_role_binding=self.cluster_role_binding.diff_from(
                other.cluster_role_binding
            ),
            cluster_role=self.cluster_role.diff_from(other.cluster_role),
            config_map=self.config_map.diff_from(other.config_map),
            cron_job=self.cron_job.diff_from(other.cron_job),
            daemon_set=self.daemon_set.diff_from(other.daemon_set),
            deployment=self.deployment.diff_from(other.deployment),
            endpoint=self.endpoint.diff_from(other.endpoint),
            ingress=self.ingress.diff_from(other.ingress),
            job=self.job.diff_from(other.job),
            network_policy=self.network_policy.diff_from(other.network_policy),
            persistent_volume_claim=self.persistent_volume_claim.diff_from(
                other.persistent_volume_claim
            ),
            persistent_volume=self.persistent_volume.diff_from(
                other.persistent_volume
            ),
            pod=self.pod.diff_from(other.pod),
            replica_set=self.replica_set.diff_from(other.replica_set),
            role_binding=self.role_binding.diff_from(other.role_binding),
            role=self.role.diff_from(other.role),
            secret=self.secret.diff_from(other.secret),
            service_account=self.service_account.diff_from(
                other.service_account
            ),
            service=self.service.diff_from(other.service),
            stateful_set=self.stateful_set.diff_from(other.stateful_set),
            storage_class=self.storage_class.diff_from(other.storage_class),
        )

    def dump(self, path: str) -> None:
        """Dump Kubernetes system state to a file"""
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.model_dump(), file, indent=4, cls=ActoEncoder)

    def check_health(self) -> KubernetesSystemHealth:
        """Check if Kubernetes system state is healthy"""
        return KubernetesSystemHealth(
            daemon_set=self.daemon_set.check_health(),
            deployment=self.deployment.check_health(),
            job=self.job.check_health(),
            pod=self.pod.check_health(),
            replica_set=self.replica_set.check_health(),
            stateful_set=self.stateful_set.check_health(),
        )
