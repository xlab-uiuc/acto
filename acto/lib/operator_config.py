from typing import List, Optional

from pydantic import BaseModel, Field


class DeployConfig(BaseModel):
    method: str
    file: str
    init: Optional[str]


class AnalysisConfig(BaseModel):
    github_link: str
    commit: str
    type: str
    package: str
    entrypoint: Optional[str]


class OperatorConfig(BaseModel):
    deploy: DeployConfig
    analysis: Optional[AnalysisConfig]

    seed_custom_resource: str
    num_nodes: int = 4
    wait_time: int = 60
    collect_coverage: bool = False
    custom_oracles: List[str] = Field(default_factory=list)
    diff_ignore_fields: List[str] = Field(default_factory=list)

    monkey_patch: Optional[str]
    custom_fields: Optional[str]
    crd_name: Optional[str]
    blackbox_custom_fields: Optional[str]
    k8s_fields: Optional[str]
    example_dir: Optional[str]
    context: Optional[str]
    focus_fields: Optional[List[List[str]]]
