import pytest

from acto.checker.impl.kubectl_cli import KubectlCliChecker, KubectlCliResult
from acto.checker.impl.tests import load_snapshot
from acto.checker.checker import OracleResult, OracleControlFlow
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = KubectlCliChecker()


def checker_func(s: Snapshot, s_prev: Snapshot) -> OracleResult:
    assert s.input != {}
    assert s_prev.input != {}
    assert s.cli_result != {}
    s.parent = s_prev
    return checker.check(s)


def test_kubectl_retry_timeout():
    stateful_checker = KubectlCliChecker()
    stateful_checker.max_retry = 1
    snapshot = load_snapshot("kubectl_cli", 99)
    snapshot_prev = load_snapshot("kubectl_cli", 99, load_prev=True)
    snapshot.parent = snapshot_prev
    # the first attempt should return redo
    oracle_result = stateful_checker.check(snapshot)
    assert oracle_result == KubectlCliResult('Connection refused, stderr: connection refused',
                                             time_to_wait_until_next_step=stateful_checker.retry_timeout,
                                             emit_by=stateful_checker.name)
    for control_flow in OracleControlFlow:
        if control_flow == OracleControlFlow.redo:
            assert oracle_result.means(control_flow)
        else:
            assert not oracle_result.means(control_flow)

    snapshot_prev = snapshot
    snapshot = load_snapshot("kubectl_cli", 99)
    snapshot.parent = snapshot_prev
    # the second attempt should return terminated because it exceeds the max_retry
    oracle_result = stateful_checker.check(snapshot)
    assert oracle_result == KubectlCliResult('Connection failed too many times. Abort',
                                             emit_by=stateful_checker.name)
    for control_flow in OracleControlFlow:
        if control_flow == OracleControlFlow.terminate:
            assert oracle_result.means(control_flow)
        else:
            assert not oracle_result.means(control_flow)


@pytest.mark.parametrize("test_case_id,expected", list(enumerate([
    (KubectlCliResult(message='Invalid input, field path: []', invalid_field_path=[]), OracleControlFlow.revert),
    (KubectlCliResult(message='Custom resource remain unchanged'), OracleControlFlow.ok),
    (KubectlCliResult(), OracleControlFlow.ok),
    (KubectlCliResult(message="Invalid input, field path: ['spec', "
                              "'allowMultipleNodesPerWorker']",
                      invalid_field_path=['spec', 'allowMultipleNodesPerWorker']), OracleControlFlow.revert)
])))
def test_check(test_case_id, expected):
    expected, expected_control_flow = expected
    expected.emit_by = "input"
    snapshot = load_snapshot("kubectl_cli", test_case_id)
    snapshot_prev = load_snapshot("kubectl_cli", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result == expected
    for control_flow in OracleControlFlow:
        if control_flow == expected_control_flow:
            assert expected.means(control_flow)
        else:
            assert not expected.means(control_flow)
