"""ClusterRole state model"""

import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesDictObject,
    list_object_helper,
)


class ClusterRoleState(KubernetesDictObject):
    """ClusterRole state object."""

    root: dict[str, kubernetes_models.V1ClusterRole]

    @classmethod
    def from_api_client(cls, api_client: kubernetes.client.ApiClient) -> Self:
        data = list_object_helper(
            kubernetes.client.RbacAuthorizationV1Api(
                api_client
            ).list_cluster_role,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check ClusterRole health"""
        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
