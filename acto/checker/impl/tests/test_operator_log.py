import pytest

from acto.checker.impl.operator_log import OperatorLogChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import OracleResult, PassResult
from acto.snapshot import Snapshot, EmptySnapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = OperatorLogChecker()


def checker_func(s: Snapshot) -> OracleResult:
    assert s.operator_log != []
    return checker.check(0, s, EmptySnapshot({}))


# TODO: Add test cases that have a responsible field
@pytest.mark.parametrize("test_case_id,result_dict", list(enumerate([
    {'responsible_field': []},
    PassResult().to_dict(),
    {'responsible_field': []},
])))
def test_check(test_case_id, result_dict):
    snapshot = load_snapshot("operator_log", test_case_id)
    oracle_result = checker_func(snapshot)
    assert oracle_result.to_dict() == result_dict
