import pytest

from acto.checker.impl.health import HealthChecker, HealthResult
from acto.checker.impl.tests import load_snapshot
from acto.checker.checker import OracleResult, OracleControlFlow
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = HealthChecker()


def checker_func(s: Snapshot) -> OracleResult:
    assert s.system_state != {}
    return checker.check(s, Snapshot({}))


@pytest.mark.parametrize("test_case_id,expected", list(enumerate([
    (HealthResult(), OracleControlFlow.ok),
    (HealthResult(), OracleControlFlow.ok),
    (HealthResult({'statefulset': ['test-cluster-server replicas [3] ready_replicas [2]']}), OracleControlFlow.revert),
    (HealthResult({'deployment': ['redis-operator replicas [1] ready_replicas [None]',
                                  'redis-operator condition [Available] status [False] message [Deployment does not '
                                  'have minimum availability.]'
                                 ],
                   'pod': ['redis-operator-54fb85ff56-ks6jl container [manager] restart_count [6]']}), OracleControlFlow.revert),
    (HealthResult({'deployment': ['rfs-test-cluster condition [Progressing] status [False] message [ReplicaSet '
                                  '"rfs-test-cluster-5dfc5484bb" has timed out progressing.]']}),
     OracleControlFlow.revert),
    (HealthResult({'pod': ['test-cluster-server-2'],
                   'statefulset': ['test-cluster-server replicas [3] ready_replicas [2]']}), OracleControlFlow.revert),
])))
def test_check(test_case_id, expected):
    expected, expected_control_flow = expected
    expected.emit_by = "health"
    snapshot = load_snapshot("health", test_case_id)
    oracle_result = checker_func(snapshot)
    assert oracle_result == expected
    for control_flow in OracleControlFlow:
        if control_flow == expected_control_flow:
            assert expected.means(control_flow)
        else:
            assert not expected.means(control_flow)

