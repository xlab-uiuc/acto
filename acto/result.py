"""Model for the result of a run of an Acto"""


import enum
import json
from typing import Optional, Union

import deepdiff
import deepdiff.helper
import pydantic
from typing_extensions import Self

from acto.common import Diff, PropertyPath
from acto.serialization import ActoEncoder
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger


class OracleResult(pydantic.BaseModel):
    """Model for the result of an oracle run"""

    message: str = pydantic.Field(description="The message of the oracle run")

    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, OracleResult)
            and self.message == __value.message
        )


class ConsistencyOracleResult(OracleResult):
    """Model for the result of a consistency oracle run"""

    input_diff: Diff = pydantic.Field(
        description="The input that caused the inconsistency"
    )
    system_state_diff: Optional[Diff] = pydantic.Field(
        serialization_alias="misssed_system_state_diff",
        description="The system state that caused the inconsistency",
        default=None,
    )

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, ConsistencyOracleResult) and (
            self.message == __value.message
            and self.input_diff == __value.input_diff
            and self.system_state_diff == __value.system_state_diff
        )


class StepID(pydantic.BaseModel):
    """Model for the ID of a step"""

    trial: str
    generation: int

    def __str__(self) -> str:
        return f"{self.trial}/{self.generation:04d}"


class DifferentialOracleResult(OracleResult):
    """Model for the result of a differential oracle run"""

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    diff: deepdiff.DeepDiff
    from_step: StepID
    from_state: dict = pydantic.Field(
        description="The state that the diff was generated from"
    )
    to_step: StepID
    to_state: dict = pydantic.Field(
        description="The state that the diff was generated to"
    )

    @pydantic.field_serializer("diff")
    def serialize_diff(self, value: deepdiff.DeepDiff):
        """Serialize the diff"""
        return value.to_dict(view_override=deepdiff.helper.TEXT_VIEW)

    def __str__(self) -> str:
        return f"{self.from_step} -> {self.to_step}: {self.message}"


class InvalidInputResult(OracleResult):
    """Model for the result of an invalid input oracle run"""

    message: str = pydantic.Field(
        description="The message of the oracle run",
        default="Invalid input detected",
    )
    responsible_property: Optional[PropertyPath] = pydantic.Field(
        description="The fields that were not present in the input",
        default=None,
    )


class OracleResults(pydantic.BaseModel):
    """The results of a collection of oracles"""

    crash: Optional[OracleResult] = pydantic.Field(
        description="The result of the crash oracle",
        default=None,
    )
    health: Optional[OracleResult] = pydantic.Field(
        description="The result of the health oracle",
        default=None,
    )
    operator_log: Optional[InvalidInputResult] = pydantic.Field(
        description="The result of the operator log oracle",
        default=None,
    )
    consistency: Optional[
        Union[ConsistencyOracleResult, InvalidInputResult]
    ] = pydantic.Field(
        description="The result of the state consistentcy oracle",
        default=None,
    )
    differential: Optional[DifferentialOracleResult] = pydantic.Field(
        description="The result of the differential oracle",
        default=None,
    )
    custom: Optional[OracleResult] = pydantic.Field(
        description="The result of the health oracle",
        default=None,
    )

    def is_error(self) -> bool:
        """Return whether the oracle results contain an error"""
        return (
            self.crash is not None
            or self.health is not None
            or self.consistency is not None
            or self.differential is not None
            or self.custom is not None
        )

    @pydantic.field_serializer("consistency")
    def serialize_consistency(
        self, value: Union[ConsistencyOracleResult, InvalidInputResult]
    ):
        """Serialize the consistency oracle result"""
        if value is None:
            return None
        return value.model_dump()


class CliStatus(enum.Enum):
    """Status of the KubeCtl CLI"""

    INVALID = "Invalid"
    UNCHANGED = "Unchanged"
    CONNECTION_REFUSED = "ConnectionRefused"
    PASS = "Pass"


def check_kubectl_cli(snapshot: Snapshot) -> CliStatus:
    """Check the output of kubectl cli command."""
    logger = get_thread_logger(with_prefix=True)

    stdout, stderr = (
        snapshot.cli_result["stdout"],
        snapshot.cli_result["stderr"],
    )

    if "unchanged" in stdout or "unchanged" in stderr:
        logger.info("CR unchanged, continue")
        return CliStatus.UNCHANGED

    if stderr == "":
        logger.info("No stderr, continue")
        return CliStatus.PASS

    if "connection refused" in stderr or "deadline exceeded" in stderr:
        logger.info("Connection refused, reject mutation")
        return CliStatus.CONNECTION_REFUSED

    return CliStatus.INVALID


def runtime_result_path(trial_dir: str, generation: int) -> str:
    """Return the path of the runtime result"""
    return f"{trial_dir}/generation-{generation:03d}-runtime.json"


class RunResult(pydantic.BaseModel):
    """Model for the runtime result of a run of an Acto.
    It mainly contains the result of the oracles, with some auxiliary information such as
    the CLI status, testcase, StepID, and whether this run is a revert."""

    testcase: dict[str, str] = pydantic.Field(
        description="The description of the testcase that was run"
    )
    step_id: StepID
    oracle_result: OracleResults
    cli_status: CliStatus
    is_revert: bool = pydantic.Field(description="Whether the run was a revert")

    def is_invalid_input(self) -> bool:
        """Return whether the run result is an invalid input"""
        return (
            self.cli_status == CliStatus.INVALID
            or isinstance(
                self.oracle_result.operator_log,
                InvalidInputResult,
            )
            or isinstance(
                self.oracle_result.consistency,
                InvalidInputResult,
            )
        )

    @pydantic.field_serializer("cli_status", return_type=str)
    def serialize_cli_status(self, value: CliStatus):
        """Serialize the CLI status"""
        return value.value

    def dump(self, trial_dir: str):
        """Dump the run result to a file"""
        with open(
            runtime_result_path(trial_dir, self.step_id.generation),
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(self.model_dump(), file, indent=4, cls=ActoEncoder)

    @classmethod
    def load(cls, trial_dir: str, generation: int) -> Self:
        """Load a run result from a file"""
        with open(
            runtime_result_path(trial_dir, generation),
            "r",
            encoding="utf-8",
        ) as file:
            return cls.model_validate(json.load(file))


class TrialResult(pydantic.BaseModel):
    """Model for the result of a trial of an Acto"""

    trial_id: str
    duration: float = pydantic.Field(
        description="The duration of the trial in seconds"
    )
    error: Optional[OracleResults] = pydantic.Field(
        description="The error that occurred during the trial",
    )

    def dump(self, filename: str):
        """Dump the trial result to a file"""
        with open(filename, "w", encoding="utf-8") as file:
            file.write(json.dumps(self.model_dump(), indent=4, cls=ActoEncoder))
