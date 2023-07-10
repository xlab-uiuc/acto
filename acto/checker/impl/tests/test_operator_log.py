import pytest

from acto.checker.impl.operator_log import OperatorLogChecker
from acto.checker.impl.tests import load_snapshot
from acto.checker.checker_result import PassResult
from acto.checker.checker import OracleResult
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = OperatorLogChecker()


def checker_func(s: Snapshot, prev_s: Snapshot) -> OracleResult:
    assert s.operator_log != []
    return checker.check(s, prev_s)


@pytest.mark.parametrize("test_case_id,result_dict", list(enumerate([
    {'responsible_field': []},
    PassResult().to_dict(),
    {'responsible_field': []},
    {'responsible_field': ['spec', 'affinity', 'podAntiAffinity', 'requiredDuringSchedulingIgnoredDuringExecution', 0, 'labelSelector', 'matchExpressions', 0, 'operator']},
])))
def test_check(test_case_id, result_dict):
    snapshot = load_snapshot("operator_log", test_case_id)
    snapshot_prev = load_snapshot("operator_log", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result.to_dict() == result_dict
