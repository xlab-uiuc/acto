import inspect
import json
import os.path
from typing import List

import yaml

from acto.snapshot import Snapshot

try:
    base_file_path = [f for f in inspect.stack() if 'test_' in f.filename][1].filename
except:
    base_file_path = __file__

base_dir = os.path.dirname(os.path.abspath(base_file_path))


def get_filename(checker_name: str, test_case_id: int, file_type: str, file_format: str, load_prev=False) -> str:
    return os.path.join(base_dir, f"{checker_name}_{file_type}_{test_case_id}{'_prev' if load_prev else ''}.{file_format}")


def get_file(checker_name: str, test_case_id: int, file_type: str, file_format: str, load_prev=False):
    file_path = get_filename(checker_name, test_case_id, file_type, file_format, load_prev)
    if not os.path.exists(file_path):
        return None
    return open(file_path)


def load_operator_log(checker_name: str, test_case_id: int, load_prev=False) -> List[str]:
    f = get_file(checker_name, test_case_id, 'operator_log', 'log', load_prev)
    if f is None:
        return []
    with f:
        return f.read().strip().splitlines()


def load_system_state(checker_name: str, test_case_id: int, load_prev=False) -> dict:
    f = get_file(checker_name, test_case_id, 'system_state', 'json', load_prev)
    if f is None:
        return {}
    with f:
        return json.load(f)


def load_cli_output(checker_name: str, test_case_id: int, load_prev=False) -> dict:
    f = get_file(checker_name, test_case_id, 'cli_output', 'log', load_prev)
    if f is None:
        return {}
    with f:
        return json.load(f)


def load_input(checker_name: str, test_case_id: int, load_prev=False) -> dict:
    f = get_file(checker_name, test_case_id, 'input', 'yaml', load_prev)
    if f is None:
        return {}
    with f:
        return yaml.safe_load(f)


def load_snapshot(checker_name: str, test_case_id: int, load_prev=False) -> Snapshot:
    return Snapshot(
        input=load_input(checker_name, test_case_id, load_prev),
        cli_result=load_cli_output(checker_name, test_case_id, load_prev),
        system_state=load_system_state(checker_name, test_case_id, load_prev),
        operator_log=load_operator_log(checker_name, test_case_id, load_prev)
    )
