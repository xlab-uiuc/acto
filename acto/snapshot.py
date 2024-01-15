from typing import Dict, List, Tuple

import pydantic
from deepdiff import DeepDiff

from acto.common import EXCLUDE_PATH_REGEX, Diff, postprocess_diff


class Snapshot(pydantic.BaseModel):
    """A snapshot of a run, including input, operator log, system state, and cli output"""

    input_cr: dict = pydantic.Field(default_factory=dict)
    cli_result: dict = pydantic.Field(default_factory=dict)
    system_state: dict = pydantic.Field(default_factory=dict)
    operator_log: List[str] = pydantic.Field(default_factory=list)
    events: dict = pydantic.Field(default_factory=dict)
    not_ready_pods_logs: dict = pydantic.Field(default_factory=dict)
    generation: int = 0

    @pydantic.model_serializer
    def serialize(self):
        """Serialize the snapshot to a dict"""
        return {
            "input": self.input_cr,
            "cli_result": self.cli_result,
            "system_state": self.system_state,
            "operator_log": self.operator_log,
        }

    def delta(
        self, prev: "Snapshot"
    ) -> Tuple[
        Dict[str, Dict[str, Diff]], Dict[str, Dict[str, Dict[str, Diff]]]
    ]:
        curr_input, curr_system_state = self.input_cr, self.system_state
        prev_input, prev_system_state = prev.input_cr, prev.system_state

        input_delta = postprocess_diff(
            DeepDiff(prev_input, curr_input, view="tree")
        )

        system_state_delta = {}
        for (
            resource_name,
            resource,
        ) in curr_system_state.items():  # pylint: disable=no-member
            if resource_name not in prev_system_state:
                prev_system_state[resource_name] = {}
            system_state_delta[resource_name] = postprocess_diff(
                DeepDiff(
                    prev_system_state[resource_name],
                    resource,
                    exclude_regex_paths=EXCLUDE_PATH_REGEX,
                    view="tree",
                )
            )

        return input_delta, system_state_delta
