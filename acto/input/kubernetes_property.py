import enum

import pydantic

from acto.common import PropertyPath


class KubernetesProperty(pydantic.BaseModel):
    """Class specifying how a property is corresponded to a Kubernetes property"""

    kubernetes_schema: str
    path: list

    def __hash__(self) -> int:
        return hash((self.kubernetes_schema, self.path))

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, KubernetesProperty):
            return False
        return (
            self.kubernetes_schema == __value.kubernetes_schema
            and self.path == __value.path
        )


class SemanticTag(enum.Enum):
    """Enum of Semantic tags, used to associate with test generators"""

    # pylint: disable=invalid-name
    Replicas = enum.auto()
    ConcurrencyPolicy = enum.auto()
    Schedule = enum.auto()
    ImagePullPolicy = enum.auto()
    Name = enum.auto()
    PreemptionPolicy = enum.auto()
    RestartPolicy = enum.auto()


KUBERNETES_TO_SEMANTIC = {
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.apps.v1.StatefulSetSpec",
        path=["replicas"],
    ): SemanticTag.Replicas,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.apps.v1.DeploymentSpec",
        path=["replicas"],
    ): SemanticTag.Replicas,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.apps.v1.DeploymentSpec",
        path=["replicas"],
    ): SemanticTag.Replicas,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.batch.v1.CronJobSpec",
        path=["concurrencyPolicy"],
    ): SemanticTag.ConcurrencyPolicy,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.batch.v1.CronJobSpec",
        path=["schedule"],
    ): SemanticTag.Schedule,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.core.v1.Container",
        path=["imagePullPolicy"],
    ): SemanticTag.ImagePullPolicy,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.core.v1.Container",
        path=["name"],
    ): SemanticTag.Name,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.core.v1.PodSpec",
        path=["preemptionPolicy"],
    ): SemanticTag.PreemptionPolicy,
    KubernetesProperty(
        kubernetes_schema="io.k8s.api.core.v1.PodSpec",
        path=["restartPolicy"],
    ): SemanticTag.RestartPolicy,
}

PROPERTY_TO_SEMANTIC: dict[PropertyPath, SemanticTag] = {}


def tag_kubernetes_property_semantic(
    kubernetes_property: KubernetesProperty, semantic_tag: SemanticTag
):
    """Tag a Kubernetes property with semantic, this is for the anonymous Kubernetes schemas"""
    KUBERNETES_TO_SEMANTIC[kubernetes_property] = semantic_tag


def tag_property_semantic(
    property_path: PropertyPath, semantic_tag: SemanticTag
):
    """Tag a property with a semantic tag"""
    PROPERTY_TO_SEMANTIC[property_path] = semantic_tag
