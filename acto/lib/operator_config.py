from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DeployMethod(str, Enum):
    YAML = 'YAML'
    HELM = 'HELM'
    KUSTOMIZE = 'KUSTOMIZE'


class DeployConfig(BaseModel, extra='forbid'):
    """Configuration for deploying the operator"""
    method: DeployMethod = DeployMethod.YAML
    file: str = Field(
        description='Path to the file for deploying the operator')
    init: Optional[str] = Field(description='Path to the init file')


class AnalysisConfig(BaseModel, extra='forbid'):
    "Configuration for static analysis"
    github_link: str = Field(
        description='HTTPS URL for cloning the operator repo')
    commit: str = Field(
        description='Commit hash to specify the version to conduct static analysis')
    type: str = Field(description='Type name of the CR')
    package: str = Field(
        description='Package name in which the type of the CR is defined')
    entrypoint: Optional[str] = Field(
        description='The relative path of the main package for the operator')


class OperatorConfig(BaseModel, extra='forbid'):
    """Configuration for porting operators to Acto"""
    deploy: DeployConfig
    analysis: Optional[AnalysisConfig] = Field(
        default=None,
        description='Configuration for static analysis')

    seed_custom_resource: str = Field(description='Path to the seed CR file')
    num_nodes: int = Field(
        description='Number of workers in the Kubernetes cluster', default=4)
    wait_time: int = Field(
        description='Timeout duration (seconds) for the resettable timer for system convergence',
        default=60)
    collect_coverage: bool = False
    custom_oracle: Optional[str] = Field(
        default=None, description='Path to the custom oracle file')
    diff_ignore_fields: List[str] = Field(default_factory=list)

    monkey_patch: Optional[str] = Field(
        default=None, description='Path to the monkey patch file')
    custom_fields: Optional[str] = Field(
        default=None, description='Path to the custom fields file')
    crd_name: Optional[str] = Field(
        default=None, description='Name of the CRD')
    blackbox_custom_fields: Optional[str] = Field(
        default=None, description='Path to the blackbox custom fields file')
    k8s_fields: Optional[str] = Field(
        default=None, description='Path to the k8s fields file')
    example_dir: Optional[str] = Field(
        default=None, description='Path to the example dir')
    context: Optional[str] = Field(
        default=None, description='Path to the context file')
    focus_fields: Optional[List[List[str]]] = Field(default=None,
                                                    description='List of focus fields')
