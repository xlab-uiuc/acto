from acto.input.input import CustomKubernetesMapping

KUBERNETES_TYPE_MAPPING: list[CustomKubernetesMapping] = [
    CustomKubernetesMapping(
        schema_path=["spec", "override", "statefulSet", "spec"],
        kubernetes_schema_name="io.k8s.api.apps.v1.StatefulSetSpec",
    ),
    CustomKubernetesMapping(
        schema_path=["spec", "override", "service", "spec"],
        kubernetes_schema_name="io.k8s.api.core.v1.ServiceSpec",
    ),
]
