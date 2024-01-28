from typing import Dict, List, Optional

from pydantic import BaseModel, Field

DELEGATED_NAMESPACE = "__DELEGATED__"


class ApplyStep(BaseModel, extra="forbid"):
    """Configuration for each step of kubectl apply"""
    file: str = Field(
        description="Path to the file for kubectl apply")
    operator: bool = Field(
        description="If the file contains the operator deployment",
        default=False)
    operator_container_name: Optional[str] = Field(
        description="The container name of the operator in the operator pod",
        default=None)
    namespace: Optional[str] = Field(
        description="Namespace for applying the file. If not specified, " +
        "use the namespace in the file or Acto namespace. " +
        "If set to null, use the namespace in the file",
        default=DELEGATED_NAMESPACE)


class WaitStep(BaseModel, extra="forbid"):
    """Configuration for each step of waiting for the operator"""
    duration: int = Field(
        description="Wait for the specified seconds",
        default=10)


class DeployStep(BaseModel, extra="forbid"):
    apply: ApplyStep = Field(
        description="Configuration for each step of kubectl apply",
        default=None)
    wait: WaitStep = Field(
        description="Configuration for each step of waiting for the operator",
        default=None)

    # TODO: Add support for helm and kustomize
    # helm: str = Field(
    #     description="Path to the file for helm install")
    # kustomize: str = Field(
    #     description="Path to the file for kustomize build")


class DeployConfig(BaseModel, extra="forbid"):
    """Configuration for deploying the operator"""
    steps: List[DeployStep] = Field(
        description="Steps to deploy the operator",
        min_length=1)


class AnalysisConfig(BaseModel, extra="forbid"):
    "Configuration for static analysis"
    github_link: str = Field(
        description="HTTPS URL for cloning the operator repo")
    commit: str = Field(
        description="Commit hash to specify the version to conduct static analysis")
    type: str = Field(description="Type name of the CR")
    package: str = Field(
        description="Package name in which the type of the CR is defined")
    entrypoint: Optional[str] = Field(
        description="The relative path of the main package for the operator, " +
                    "required if the main is not in the root directory")


class KubernetesEngineConfig(BaseModel, extra="forbid"):
    feature_gates: Dict[str, bool] = Field(
        description="Path to the feature gates file", default=None)


class OperatorConfig(BaseModel, extra="forbid"):
    """Configuration for porting operators to Acto"""
    deploy: DeployConfig
    analysis: Optional[AnalysisConfig] = Field(
        default=None,
        description="Configuration for static analysis")

    seed_custom_resource: str = Field(description="Path to the seed CR file")
    num_nodes: int = Field(
        description="Number of workers in the Kubernetes cluster", default=4)
    wait_time: int = Field(
        description="Timeout duration (seconds) for the resettable timer for system convergence",
        default=60)
    collect_coverage: bool = False
    custom_oracle: Optional[str] = Field(
        default=None, description="Path to the custom oracle file")
    diff_ignore_fields: Optional[List[str]] = Field(default_factory=list)
    kubernetes_version: str = Field(
        default="v1.22.9", description="Kubernetes version")
    kubernetes_engine: KubernetesEngineConfig = Field(
        default=KubernetesEngineConfig(),
        description="Configuration for the Kubernetes engine")

    monkey_patch: Optional[str] = Field(
        default=None, description="Path to the monkey patch file")
    custom_fields: Optional[str] = Field(
        default=None, description="Path to the custom fields file")
    crd_name: Optional[str] = Field(
        default=None, description="Name of the CRD")
    blackbox_custom_fields: Optional[str] = Field(
        default=None, description="Path to the blackbox custom fields file")
    k8s_fields: Optional[str] = Field(
        default=None, description="Path to the k8s fields file")
    example_dir: Optional[str] = Field(
        default=None, description="Path to the example dir")
    context: Optional[str] = Field(
        default=None, description="Path to the context file")
    focus_fields: Optional[List[List[str]]] = Field(
        default=None, description="List of focus fields")


if __name__ == "__main__":
    import json

    import jsonref
    print(
        json.dumps(
            jsonref.replace_refs(
                OperatorConfig.model_json_schema()),
            indent=4))
