"""StatefulSet state model."""

import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesNamespacedDictObject,
    list_namespaced_object_helper,
)


class StatefulSetState(KubernetesNamespacedDictObject):
    """StatefulSet state object."""

    root: dict[str, kubernetes_models.V1StatefulSet]

    @classmethod
    def from_api_client_namespaced(
        cls, api_client: kubernetes.client.ApiClient, namespace: str
    ) -> Self:
        data = list_namespaced_object_helper(
            kubernetes.client.AppsV1Api(
                api_client
            ).list_namespaced_stateful_set,
            namespace,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check if StatefulSet is healthy

        Returns:
            tuple[bool, str]: (is_healthy, reason)
        """

        for name, stateful_set in self.root.items():
            if (
                stateful_set.status.observed_generation
                != stateful_set.metadata.generation
            ):
                return False, f"StatefulSet[{name}] generation mismatch"

            if (
                stateful_set.status.current_revision
                != stateful_set.status.update_revision
            ):
                return (
                    False,
                    f"StatefulSet[{name}] revision mismatch"
                    + f"current[{stateful_set.status.current_revision}] "
                    + f"!= update[{stateful_set.status.update_revision}]",
                )

            if stateful_set.spec.replicas != stateful_set.status.ready_replicas:
                return False, f"StatefulSet[{name}] replicas mismatch"

            if stateful_set.status.conditions is not None:
                for condition in stateful_set.status.conditions:
                    if condition.type == "Ready" and condition.status != "True":
                        return (
                            False,
                            f"StatefulSet[{name}] is not ready: {condition.message}",
                        )

        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
