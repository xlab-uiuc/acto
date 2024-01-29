"""ClusterRoleBinding state model"""

import kubernetes
import kubernetes.client.models as kubernetes_models
import pydantic
from kubernetes.client.api_client import ApiClient
from typing_extensions import Self

from acto.system_state.kubernetes_object import (
    KubernetesDictObject,
    list_object_helper,
)


class ClusterRoleBindingState(KubernetesDictObject):
    """ClusterRoleBinding state object."""

    root: dict[str, kubernetes_models.V1ClusterRoleBinding]

    @classmethod
    def from_api_client(cls, api_client: ApiClient) -> Self:
        data = list_object_helper(
            kubernetes.client.RbacAuthorizationV1Api(
                api_client
            ).list_cluster_role_binding,
        )
        return cls.model_validate(data)

    def check_health(self) -> tuple[bool, str]:
        """Check ClusterRoleBinding health"""
        return True, ""

    @pydantic.model_serializer
    def serialize(self):
        return {key: value.to_dict() for key, value in self.root.items()}
