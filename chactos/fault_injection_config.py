import pydantic

from acto.lib.operator_config import DeployConfig


class FaultInjectionConfig(pydantic.BaseModel, extra="forbid"):
    """Fault Injection Config"""

    deploy: DeployConfig
    application_selector: dict
    operator_selector: dict
    pod_prefix: str
    input_dir: str
