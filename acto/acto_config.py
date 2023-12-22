"""This module contains the configuration schema for the acto tool.
"""

import os
from typing import Literal

import pydantic
import yaml

ACTO_CONFIG_PATH = os.environ.get("ACTO_CONFIG_PATH") or "config.yaml"


class AlarmsConfig(pydantic.BaseModel):
    """Configuration for reporting alarms"""

    invalid_input: bool = pydantic.Field(
        default=True,
        description="Report alarms for invalid input",
    )
    warning_in_operator_logs: bool = pydantic.Field(
        default=False,
        description="Report alarms for warnings in operator logs",
    )


class CrashNotificationConfig(pydantic.BaseModel):
    """Configuration for crash notification"""

    enabled: bool = False


class StateCheckerAnalysisMode(pydantic.BaseModel):
    """Configuration for state checker analysis mode"""

    dependency: bool = pydantic.Field(
        default=False,
        description="Enable dependency analysis",
    )
    taint: bool = False


class StateCheckerConfig(pydantic.BaseModel):
    """Configuration for state checker"""

    enable_canonicalization: bool = pydantic.Field(
        default=True,
        description="Enable value canonicalization for property comparison",
    )
    enable_default_value_comparison: bool = pydantic.Field(
        default=True,
        description="Enable to consider default values when doing property comparison",
    )
    analysis: StateCheckerAnalysisMode = pydantic.Field(
        default_factory=StateCheckerAnalysisMode,
        description="Configuration for state checker analysis mode",
    )


class CheckerConfig(pydantic.BaseModel):
    """Configuration for oracle checkers"""

    state: StateCheckerConfig = pydantic.Field(
        default_factory=StateCheckerConfig,
        description="Configuration for state checker",
    )


class ActoConfig(pydantic.BaseModel):
    """Configuration for Acto"""

    alarms: AlarmsConfig = pydantic.Field(
        default_factory=AlarmsConfig,
        description="Configuration for reporting alarms",
    )
    checkers: CheckerConfig = pydantic.Field(
        default_factory=CheckerConfig,
        description="Configuration for oracle checkers",
    )
    mode: Literal["whitebox", "blackbox"] = pydantic.Field(
        default="whitebox",
        description="whitebox or blackbox"
        + "whitebox: Acto will conduct static analysis"
        + "blackbox: Acto will not conduct static analysis",
    )
    notifications: CrashNotificationConfig = pydantic.Field(
        default_factory=CrashNotificationConfig,
        description="Configuration for crash notification",
    )
    strict: bool = True


def load_config() -> ActoConfig:
    """Load configuration from a yaml file"""

    if os.path.exists(ACTO_CONFIG_PATH):
        with open(ACTO_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return ActoConfig.model_validate(config)
    return ActoConfig()


ACTO_CONFIG: ActoConfig = load_config()
