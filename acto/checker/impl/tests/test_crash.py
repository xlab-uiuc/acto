import pytest

from acto.checker.impl.crash import CrashChecker
from acto.checker.impl.tests import load_snapshot
from acto.checker.checker import OracleResult, OracleControlFlow
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = CrashChecker()


def checker_func(s: Snapshot) -> OracleResult:
    assert s.system_state != {}
    return checker.check(s, Snapshot({}))


@pytest.mark.parametrize("test_case_id,expected", list(enumerate([
    (OracleResult('Pod test-cluster-server-2 crashed'), OracleControlFlow.revert),
    (OracleResult(), OracleControlFlow.ok)
])))
def test_check(test_case_id, expected):
    expected, expected_control_flow = expected
    expected.emit_by = "crash"
    snapshot = load_snapshot("crash", test_case_id)
    oracle_result = checker_func(snapshot)
    assert oracle_result == expected
    for control_flow in OracleControlFlow:
        if control_flow == expected_control_flow:
            assert expected.means(control_flow)
        else:
            assert not expected.means(control_flow)
