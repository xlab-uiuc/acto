from acto.input.input import CustomKubernetesMapping

KUBERNETES_TYPE_MAPPING: list[CustomKubernetesMapping] = [
    CustomKubernetesMapping(
        schema_path=["spec", "backupRepositories", "ITEM", "volume", "source"],
        kubernetes_schema_name="io.k8s.api.core.v1.Volume",
    ),
    CustomKubernetesMapping(
        schema_path=[
            "spec",
            "customSolrKubeOptions",
            "podOptions",
            "volumes",
            "ITEM",
        ],
        kubernetes_schema_name="io.k8s.api.core.v1.Volume",
    ),
]
