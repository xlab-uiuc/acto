import glob
import json
import os
from typing import Dict, Tuple

import pytest
import yaml
from deepdiff.helper import NotPresent

from acto.checker.impl.state import StateChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import PassResult, OracleResult, StateResult, Oracle, Diff, InvalidInputResult
from acto.input import DeterministicInputModel
from acto.lib.dict import visit_dict
from acto.snapshot import Snapshot


@lambda _: _()
def input_model_and_context_mapping():
    configs = glob.glob('./data/**/config.json')
    mapping = {}
    for config_path in configs:
        config = json.load(open(config_path))
        seed_path = config['seed_custom_resource']
        seed = yaml.safe_load(open(seed_path))
        key = seed['apiVersion']

        context_path = os.path.join(os.path.dirname(os.path.abspath(config_path)), 'context.json')
        context = json.load(open(context_path))

        used_fields, ok = visit_dict(context, ['analysis_result', 'used_fields'])
        if not ok:
            used_fields = []

        input_model = DeterministicInputModel(
            context['crd']['body'], used_fields,
            None, 1, 1, None)
        mapping[key] = (context, input_model)
    return mapping


input_model_and_context_mapping: Dict[str, Tuple[Dict, DeterministicInputModel]]


def checker_func(s: Snapshot, prev_s: Snapshot) -> OracleResult:
    api_version = s.input['apiVersion']
    checker = StateChecker(trial_dir="",
                           input_model=input_model_and_context_mapping[api_version][1],
                           context=input_model_and_context_mapping[api_version][0])
    checker.write_delta_log = lambda *args: None
    return checker.check(0, s, prev_s)


@pytest.mark.parametrize("test_case_id,result_dict", list(enumerate([
    StateResult(Oracle.SYSTEM_STATE, 'Found no matching fields for input', Diff(NotPresent(), "ACTOKEY", ['spec', 'additionalServiceConfig', 'nodePortService', 'additionalAnnotations', 'ACTOKEY'])),
    PassResult(),
    InvalidInputResult([]),
    PassResult(),
    PassResult(),
    PassResult(),
    PassResult(),
    PassResult(),
    StateResult(Oracle.SYSTEM_STATE, 'Found no matching fields for input', Diff(NotPresent(), ".399015Gi", ['spec', 'sidecars', 0, 'env', 1, 'valueFrom', 'resourceFieldRef', 'divisor'])),
])))
def test_check(test_case_id, result_dict):
    snapshot = load_snapshot("state", test_case_id)
    snapshot_prev = load_snapshot("state", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result == result_dict
