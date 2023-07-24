import pytest

from acto.checker.impl.tests import load_snapshot, set_base_dir, unset_base_dir
from acto.checker.checker import OracleResult, OracleControlFlow
from acto.snapshot import Snapshot
from oracle import JavaExceptionLogChecker

# Crash checker is stateless, so we can use the same instance for all tests
checker = JavaExceptionLogChecker()


def checker_func(s: Snapshot) -> OracleResult:
    assert s.operator_log != []
    return checker.check(s)


@pytest.mark.parametrize("test_case_id,expected_control_flow", list(enumerate([
    OracleControlFlow.revert,
])))
def test_check(test_case_id, expected_control_flow):
    set_base_dir()
    snapshot = load_snapshot(checker.name, test_case_id)
    oracle_result = checker_func(snapshot)
    assert oracle_result.means(expected_control_flow)
    for control_flow in OracleControlFlow:
        if control_flow != expected_control_flow:
            assert not oracle_result.means(control_flow)
    unset_base_dir()
