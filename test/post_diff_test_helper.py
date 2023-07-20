import glob
import json
import os.path
from typing import Generator, Tuple, Union, List

import yaml

from acto.checker.checker import OracleResult
from acto.snapshot import Snapshot

def move_revert_case_last(path:str):
    return path.replace('--1', '-a')

class FileBasedTrial:
    def __init__(self, work_dir: str):
        system_inputs = sorted(glob.glob(os.path.join(work_dir, 'mutated-*.yaml')), key=move_revert_case_last)
        self.system_input = list(map(yaml.safe_load, map(open, system_inputs)))

        cli_output = sorted(glob.glob(os.path.join(work_dir, 'cli-output-*.log')), key=move_revert_case_last)
        self.cli_output = list(map(json.load, map(open, cli_output)))

        operator_log = sorted(glob.glob(os.path.join(work_dir, 'operator-*.log')), key=move_revert_case_last)
        self.operator_log = list(map(lambda p: open(p).read().strip().splitlines(), operator_log))

        system_state = sorted(glob.glob(os.path.join(work_dir, 'system-state-*.json')), key=move_revert_case_last)
        self.system_state = list(map(json.load, map(open, system_state)))

    def history_iterator(self) -> Generator[Tuple[Tuple[dict, dict], Union[Exception, Tuple[Snapshot, List[OracleResult]]]], None, None]:
        for (system_input, cli_output, operator_log, system_state) in zip(self.system_input, self.cli_output, self.operator_log, self.system_state):
            yield (system_input, {}), (Snapshot(system_state=system_state,
                                                input=system_input,
                                                operator_log=operator_log,
                                                cli_result=cli_output), [])

class DiffTestResultTrial:
    def __init__(self, diff_test_result: dict):
        diff_test_result = diff_test_result['snapshot']
        self.system_input = [diff_test_result['input']]
        self.cli_output = [diff_test_result['cli_result']]
        self.operator_log = [diff_test_result['operator_log']]
        self.system_state = [diff_test_result['system_state']]

    def history_iterator(self) -> Generator[Tuple[Tuple[dict, dict], Union[Exception, Tuple[Snapshot, List[OracleResult]]]], None, None]:
        for (system_input, cli_output, operator_log, system_state) in zip(self.system_input, self.cli_output, self.operator_log, self.system_state):
            yield (system_input, {}), (Snapshot(system_state=system_state,
                                                input=system_input,
                                                operator_log=operator_log,
                                                cli_result=cli_output), [])