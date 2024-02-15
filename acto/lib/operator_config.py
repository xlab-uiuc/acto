from typing import Optional

import pydantic

DELEGATED_NAMESPACE = "__DELEGATED__"


class ApplyStep(pydantic.BaseModel, extra="forbid"):
    """Configuration for each step of kubectl apply"""

    file: str = pydantic.Field(description="Path to the file for kubectl apply")
    operator: bool = pydantic.Field(
        description="If the file contains the operator deployment",
        default=False,
    )
    operator_container_name: Optional[str] = pydantic.Field(
        description="The container name of the operator in the operator pod, "
        "required if there are multiple containers in the operator pod",
        default=None,
    )
    namespace: Optional[str] = pydantic.Field(
        description="Namespace for applying the file. If not specified, "
        + "use the namespace in the file or Acto namespace. "
        + "If set to null, use the namespace in the file",
        default=DELEGATED_NAMESPACE,
    )


class WaitStep(pydantic.BaseModel, extra="forbid"):
    """Configuration for each step of waiting for the operator"""

    duration: int = pydantic.Field(
        description="Wait for the specified seconds", default=10
    )


class DeployStep(pydantic.BaseModel, extra="forbid"):
    """A step of deploying a resource"""

    apply: ApplyStep = pydantic.Field(
        description="Configuration for each step of kubectl apply", default=None
    )
    wait: WaitStep = pydantic.Field(
        description="Configuration for each step of waiting for the operator",
        default=None,
    )

    # TODO: Add support for helm and kustomize
    # helm: str = pydantic.Field(
    #     description="Path to the file for helm install")
    # kustomize: str = pydantic.Field(
    #     description="Path to the file for kustomize build")


class DeployConfig(pydantic.BaseModel, extra="forbid"):
    """Configuration for deploying the operator"""

    steps: list[DeployStep] = pydantic.Field(
        description="Steps to deploy the operator", min_length=1
    )


class AnalysisConfig(pydantic.BaseModel, extra="forbid"):
    "Configuration for static analysis"
    github_link: str = pydantic.Field(
        description="HTTPS URL for cloning the operator repo"
    )
    commit: str = pydantic.Field(
        description="Commit hash to specify the version to conduct static analysis"
    )
    type: str = pydantic.Field(description="Type name of the CR")
    package: str = pydantic.Field(
        description="Package name in which the type of the CR is defined"
    )
    entrypoint: Optional[str] = pydantic.Field(
        description="The relative path of the main package for the operator, "
        + "required if the main is not in the root directory"
    )


class KubernetesEngineConfig(pydantic.BaseModel, extra="forbid"):
    """Configuration for Kubernetes"""

    feature_gates: dict[str, bool] = pydantic.Field(
        description="Path to the feature gates file", default=None
    )


class OperatorConfig(pydantic.BaseModel, extra="forbid"):
    """Configuration for porting operators to Acto"""

    deploy: DeployConfig
    analysis: Optional[AnalysisConfig] = pydantic.Field(
        default=None, description="Configuration for static analysis"
    )

    seed_custom_resource: str = pydantic.Field(
        description="Path to the seed CR file"
    )
    num_nodes: int = pydantic.Field(
        description="Number of workers in the Kubernetes cluster", default=4
    )
    wait_time: int = pydantic.Field(
        description="Timeout duration (seconds) for the resettable timer for system convergence",
        default=60,
    )
    collect_coverage: bool = False
    custom_oracle: Optional[str] = pydantic.Field(
        default=None, description="Path to the custom oracle file"
    )
    diff_ignore_fields: Optional[list[str]] = pydantic.Field(
        default_factory=list
    )
    kubernetes_version: str = pydantic.Field(
        default="v1.28.0", description="Kubernetes version"
    )
    kubernetes_engine: KubernetesEngineConfig = pydantic.Field(
        default=KubernetesEngineConfig(),
        description="Configuration for the Kubernetes engine",
    )
    monkey_patch: Optional[str] = pydantic.Field(
        default=None, description="Path to the monkey patch file"
    )
    custom_module: Optional[str] = pydantic.Field(
        default=None,
        description="Path to the custom module, in the Python module path format",
    )
    crd_name: Optional[str] = pydantic.Field(
        default=None,
        description="Name of the CRD, required if there are multiple CRDs",
    )
    example_dir: Optional[str] = pydantic.Field(
        default=None, description="Path to the example dir"
    )
    context: Optional[str] = pydantic.Field(
        default=None, description="Path to the context file"
    )
    focus_fields: Optional[list[list[str]]] = pydantic.Field(
        default=None, description="List of focus fields"
    )


if __name__ == "__main__":
    import json

    import jsonref

    print(
        json.dumps(
            jsonref.replace_refs(OperatorConfig.model_json_schema()), indent=4
        )
    )
