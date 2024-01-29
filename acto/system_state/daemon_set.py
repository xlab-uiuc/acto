"""DaemonSet state model"""
import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesNamespacedDictObject,
    list_namespaced_object_helper,
)


class DaemonSetState(KubernetesNamespacedDictObject):
    """DaemonSet state object."""

    root: dict[str, kubernetes_models.V1DaemonSet]

    @classmethod
    def from_api_client_namespaced(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        data = list_namespaced_object_helper(
            kubernetes.client.AppsV1Api(api_client).list_namespaced_daemon_set,
            namespace,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check if DaemonSet is healthy

        Returns:
            tuple[bool, str]: (is_healthy, reason)
        """

        for name, daemon_set in self.root.items():
            if (
                daemon_set.status.observed_generation
                != daemon_set.metadata.generation
            ):
                return False, f"DaemonSet[{name}] generation mismatch"

            if (
                daemon_set.status.desired_number_scheduled
                != daemon_set.status.number_ready
            ):
                return (
                    False,
                    f"DaemonSet[{name}] replicas mismatch, "
                    + f"desired[{daemon_set.status.desired_number_scheduled}] "
                    + f"!= ready[{daemon_set.status.number_ready}]",
                )

            if daemon_set.status.conditions is not None:
                for condition in daemon_set.status.conditions:
                    if (
                        condition.type == "Progressing"
                        and condition.status != "True"
                    ):
                        return (
                            False,
                            f"DaemonSet[{name}] is not progressing: {condition.message}",
                        )

        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
