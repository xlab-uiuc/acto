from typing import Optional

import pydantic
from typing_extensions import Self

from acto.input.constraint import XorCondition

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


class HelmInstallStep(pydantic.BaseModel, extra="forbid"):
    """Configuration for each step of helm install"""

    release_name: str = pydantic.Field(
        description="Name of the release for helm install",
        default="operator-release",
    )
    chart: str = pydantic.Field(
        description="Path to the chart for helm install"
    )
    namespace: Optional[str] = pydantic.Field(
        description="Namespace for installing the chart. If not specified, "
        + "use the namespace in the chart or Acto namespace. "
        + "If set to null, use the namespace in the chart",
        default=DELEGATED_NAMESPACE,
    )
    repo: Optional[str] = pydantic.Field(
        description="Name of the helm repository", default=None
    )
    version: Optional[str] = pydantic.Field(
        description="Version of the helm chart", default=None
    )
    operator: bool = pydantic.Field(
        description="If the file contains the operator deployment",
        default=False,
    )
    operator_deployment_name: Optional[str] = pydantic.Field(
        description="The deployment name of the operator in the operator pod, "
        "required if there are multiple deployments in the operator pod",
        default=None,
    )
    operator_container_name: Optional[str] = pydantic.Field(
        description="The container name of the operator in the operator pod, "
        "required if there are multiple containers in the operator pod",
        default=None,
    )

    @pydantic.model_validator(mode="after")
    def check_operator_helm_install(self) -> Self:
        """Check if the operator helm install is valid"""
        if self.operator:
            if (
                not self.operator_deployment_name
                or not self.operator_container_name
            ):
                raise ValueError(
                    "operator_deployment_name and operator_container_name "
                    + "are required for operator helm install for operator"
                )
        return self


class DeployStep(pydantic.BaseModel, extra="forbid"):
    """A step of deploying a resource"""

    apply: Optional[ApplyStep] = pydantic.Field(
        description="Configuration for each step of kubectl apply", default=None
    )
    wait: Optional[WaitStep] = pydantic.Field(
        description="Configuration for each step of waiting for the operator",
        default=None,
    )
    helm_install: Optional[HelmInstallStep] = pydantic.Field(
        description="Configuration for each step of helm install", default=None
    )

    # TODO: Add support and kustomize
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
    crd_version: Optional[str] = pydantic.Field(
        default=None,
        description="Version of the CRD, required if there are multiple CRD versions",
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
    constraints: Optional[list[XorCondition]] = pydantic.Field(
        default=None, description="List of constraints"
    )


if __name__ == "__main__":
    import json

    import jsonref

    print(
        json.dumps(
            jsonref.replace_refs(OperatorConfig.model_json_schema()), indent=4
        )
    )
