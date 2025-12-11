from acto.input.input import CustomKubernetesMapping

KUBERNETES_TYPE_MAPPING: list[CustomKubernetesMapping] = [
    CustomKubernetesMapping(
        schema_path=["spec"],
        kubernetes_schema_name="io.k8s.api.apps.v1.DeploymentSpec",
    ),
]
