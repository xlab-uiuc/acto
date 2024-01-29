"""ReplicaSet state model."""
import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesNamespacedDictObject,
    list_namespaced_object_helper,
)


class ReplicaSetState(KubernetesNamespacedDictObject):
    """ReplicaSet state object."""

    root: dict[str, kubernetes_models.V1ReplicaSet]

    @classmethod
    def from_api_client_namespaced(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        data = list_namespaced_object_helper(
            kubernetes.client.AppsV1Api(api_client).list_namespaced_replica_set,
            namespace,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check if ReplicaSet is healthy

        Returns:
            tuple[bool, str]: (is_healthy, reason)
        """
        for name, replica_set in self.root.items():
            if (
                replica_set.status.observed_generation
                != replica_set.metadata.generation
            ):
                return False, f"ReplicaSet[{name}] generation mismatch"

            if replica_set.spec.replicas != replica_set.status.ready_replicas:
                return False, f"ReplicaSet[{name}] replicas mismatch"

            for condition in replica_set.status.conditions:
                if condition.type == "Available" and condition.status != "True":
                    return False, f"ReplicaSet[{name}] is not available"

        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
