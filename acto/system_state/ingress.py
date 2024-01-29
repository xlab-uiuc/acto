"""Ingress state model"""
import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesNamespacedDictObject,
    list_namespaced_object_helper,
)


class IngressState(KubernetesNamespacedDictObject):
    """Ingress state object."""

    root: dict[str, kubernetes_models.V1Ingress]

    @classmethod
    def from_api_client_namespaced(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        data = list_namespaced_object_helper(
            kubernetes.client.NetworkingV1Api(
                api_client
            ).list_namespaced_ingress,
            namespace,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check if Ingress is healthy

        Returns:
            tuple[bool, str]: (is_healthy, reason)
        """

        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
