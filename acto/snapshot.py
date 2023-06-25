from functools import lru_cache
from typing import Tuple, Dict

from deepdiff import DeepDiff

from acto.common import postprocess_diff, EXCLUDE_PATH_REGEX, Diff


class Snapshot:
    def __init__(self, input: dict, cli_result: dict, system_state: dict, operator_log: list[str]):
        self.input = input
        self.cli_result = cli_result
        self.system_state = system_state
        self.operator_log = operator_log

    def to_dict(self):
        return {
            'input': self.input,
            'cli_result': self.cli_result,
            'system_state': self.system_state,
            'operator_log': self.operator_log
        }

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


def EmptySnapshot(input: dict):
    return Snapshot(input, {}, {}, [])
