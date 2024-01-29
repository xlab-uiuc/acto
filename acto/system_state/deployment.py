"""Deployment state model"""
import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesNamespacedDictObject,
    list_namespaced_object_helper,
)


class DeploymentState(KubernetesNamespacedDictObject):
    """Deployment state model"""

    root: dict[str, kubernetes_models.V1Deployment]

    @classmethod
    def from_api_client_namespaced(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        data = list_namespaced_object_helper(
            kubernetes.client.AppsV1Api(api_client).list_namespaced_deployment,
            namespace,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check if deployment is healthy

        Returns:
            tuple[bool, str]: (is_healthy, reason)
        """

        for name, deployment in self.root.items():
            if (
                deployment.status.observed_generation
                != deployment.metadata.generation
            ):
                return False, f"Deployment[{name}] generation mismatch"

            if deployment.spec.replicas != deployment.status.ready_replicas:
                return False, f"Deployment[{name}] replicas mismatch"

            if deployment.status.conditions is not None:
                for condition in deployment.status.conditions:
                    if (
                        condition.type == "Available"
                        and condition.status != "True"
                    ):
                        return False, f"Deployment[{name}] is not available"
                    if (
                        condition.type == "Progressing"
                        and condition.status != "True"
                    ):
                        return False, f"Deployment[{name}] is not progressing"

            if deployment.status.replicas != deployment.status.ready_replicas:
                return False, f"Deployment[{name}] replicas mismatch"

            if (
                deployment.status.unavailable_replicas != 0
                and deployment.status.unavailable_replicas is not None
            ):
                return (
                    False,
                    f"[{name}] [{deployment.status.unavailable_replicas}] pods are unavailable",
                )

        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
