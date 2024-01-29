"""Pod state model"""
import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesNamespacedDictObject,
    list_namespaced_object_helper,
)


class PodState(KubernetesNamespacedDictObject):
    """Pod state model"""

    root: dict[str, kubernetes_models.V1Pod]

    @classmethod
    def from_api_client_namespaced(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        data = list_namespaced_object_helper(
            kubernetes.client.CoreV1Api(api_client).list_namespaced_pod,
            namespace,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check if pod is healthy

        Returns:
            tuple[bool, str]: (is_healthy, reason)
        """

        for name, pod in self.root.items():
            if pod.status.conditions is not None:
                for condition in pod.status.conditions:
                    if condition.type == "Ready" and condition.status != "True":
                        return (
                            False,
                            f"Pod[{name}] is not ready: {condition.message}",
                        )

            if pod.status.container_statuses is not None:
                for container_status in pod.status.container_statuses:
                    if container_status.ready is not True:
                        return (
                            False,
                            f"Container {container_status.name} is not ready",
                        )

            if pod.status.init_container_statuses is not None:
                for container_status in pod.status.init_container_statuses:
                    if container_status.ready is not True:
                        return (
                            False,
                            f"Init container {container_status.name} is not ready",
                        )

        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
