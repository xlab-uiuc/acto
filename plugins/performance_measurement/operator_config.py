from pydantic import BaseModel, Field

from acto.lib.operator_config import DeployConfig


class AnvilControllerConfig(BaseModel, extra="forbid"):
    """Configuration for porting operators to Acto"""

    deploy: DeployConfig
    num_nodes: int = Field(
        description="Number of workers in the Kubernetes cluster", default=4
    )
    kubernetes_version: str = Field(
        default="v1.22.9", description="Kubernetes version"
    )
