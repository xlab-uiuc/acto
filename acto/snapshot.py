from dataclasses import dataclass, field
from functools import lru_cache
from typing import Tuple, Dict, List, TypedDict, Optional, Literal

from deepdiff import DeepDiff

from acto.common import postprocess_diff, EXCLUDE_PATH_REGEX, Diff


class PodLog(TypedDict):
    log: Optional[List[str]]
    previous_log: Optional[List[str]]


@dataclass
class Snapshot:
    input: dict = field(default_factory=dict)
    cli_result: dict = field(default_factory=dict)
    system_state: dict = field(default_factory=dict)
    operator_log: List[str] = field(default_factory=list)
    events: dict = field(default_factory=dict)
    not_ready_pods_logs: dict = field(default_factory=dict)
    generation: int = 0
    trial_state: Literal['normal', 'recovering', 'terminated', 'runtime_exception'] = 'normal'
    snapshot_before_applied_input: Optional['Snapshot'] = None

    @lru_cache
    def delta(self, prev: 'Snapshot') -> Tuple[Dict[str, Dict[str, Dict[str, Diff]]], Dict[str, Dict[str, Dict[str, Diff]]]]:
        curr_input, curr_system_state = self.input, self.system_state
        prev_input, prev_system_state = prev.input, prev.system_state

        input_delta = postprocess_diff(DeepDiff(prev_input, curr_input, view='tree'))

        system_state_delta = {}
        for resource in curr_system_state:
            if resource not in prev_system_state:
                prev_system_state[resource] = {}
            system_state_delta[resource] = postprocess_diff(
                DeepDiff(prev_system_state[resource],
                         curr_system_state[resource],
                         exclude_regex_paths=EXCLUDE_PATH_REGEX,
                         view='tree'))

        return input_delta, system_state_delta

    def set_snapshot_before_applied_input(self, snapshot: 'Snapshot'):
        self.snapshot_before_applied_input = snapshot
