import glob
import json
import os
from typing import Dict, Tuple

from acto.common import Diff

import pytest
import yaml
from deepdiff.helper import NotPresent

from acto.checker.impl.state import StateChecker, StateResult
from acto.checker.impl.tests import load_snapshot
from acto.checker.checker import OracleResult, OracleControlFlow
from acto.input import DeterministicInputModel
from acto.lib.dict import visit_dict
from acto.snapshot import Snapshot


def input_model_and_context_mapping() -> Dict[str, Tuple[Dict, DeterministicInputModel]]:
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


mapping = input_model_and_context_mapping()


def checker_func(s: Snapshot, prev_s: Snapshot) -> OracleResult:
    api_version = s.input['apiVersion']
    checker = StateChecker(trial_dir="",
                           input_model=mapping[api_version][1],
                           context=mapping[api_version][0])
    checker.write_delta_log = lambda *args: None
    return checker.check(s, prev_s)


@pytest.mark.parametrize("test_case_id,expected", list(enumerate([
    (StateResult(message='Found no matching fields for input',
                 diff=Diff(prev=NotPresent(),
                           curr='ACTOKEY',
                           path=['spec',
                                 'additionalServiceConfig',
                                 'nodePortService',
                                 'additionalAnnotations',
                                 'ACTOKEY'])
                 ), OracleControlFlow.revert),
    (StateResult(), OracleControlFlow.ok),
    (StateResult(message='Invalid input from status message: StatefulSet.apps '
                         '"test-cluster-server" is invalid: '
                         'spec.template.spec.restartPolicy: Unsupported value: '
                         '"OnFailure": supported values: "Always"',
                 diff=Diff(prev='Finish reconciling',
                           curr='StatefulSet.apps "test-cluster-server" is invalid: '
                                'spec.template.spec.restartPolicy: Unsupported '
                                'value: "OnFailure": supported values: "Always"',
                           path=['conditions', 3, 'message']),
                 invalid_field_path=[]
                 ), OracleControlFlow.revert),
    (StateResult(), OracleControlFlow.ok),
    (StateResult(), OracleControlFlow.ok),
    (StateResult(), OracleControlFlow.ok),
    (StateResult(), OracleControlFlow.ok),
    (StateResult(), OracleControlFlow.ok),
    (StateResult(message='Found no matching fields for input',
                 diff=Diff(prev=NotPresent(),
                           curr='.399015Gi',
                           path=['spec',
                                 'sidecars',
                                 0,
                                 'env',
                                 1,
                                 'valueFrom',
                                 'resourceFieldRef',
                                 'divisor'])
                 ), OracleControlFlow.revert),

])))
def test_check(test_case_id, expected):
    expected, expected_control_flow = expected
    expected.emit_by = "state"
    snapshot = load_snapshot("state", test_case_id)
    snapshot_prev = load_snapshot("state", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result == expected
    for control_flow in OracleControlFlow:
        if control_flow == expected_control_flow:
            assert expected.means(control_flow)
        else:
            assert not expected.means(control_flow)
