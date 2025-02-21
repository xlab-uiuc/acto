import enum
from typing import Optional

import pydantic


class FaultType(enum.Enum):
    """Fault Type"""

    POD_FAILURE = "pod_failure"
    NETWORK_DELAY = "network_failure"


class FaultInjectionConfig(pydantic.BaseModel, extra="forbid"):
    """Fault Injection Config"""

    application_selector: dict
    priority_application_selector: Optional[dict] = None
    operator_selector: dict
    application_data_dir: str
    pod_failure_ratio: float = 1.0
    fault_type: FaultType
