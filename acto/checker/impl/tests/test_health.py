import pytest

from acto.checker.impl.health import HealthChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import OracleResult, PassResult, UnhealthyResult, Oracle
from acto.snapshot import Snapshot, EmptySnapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = HealthChecker()


def checker_func(s: Snapshot) -> OracleResult:
    assert s.system_state != {}
    return checker.check(0, s, EmptySnapshot({}))


@pytest.mark.parametrize("test_case_id,result_dict", list(enumerate([
    PassResult().to_dict(),
    PassResult().to_dict(),
    UnhealthyResult(Oracle.SYSTEM_HEALTH, 'statefulset: test-cluster-server replicas [3] ready_replicas [2]').to_dict(),
    UnhealthyResult(Oracle.SYSTEM_HEALTH, 'deployment: redis-operator replicas [1] ready_replicas [None], '
                                          'redis-operator condition [Available] status [False] message '
                                          '[Deployment does not have minimum availability.]\n'
                                          'pod: redis-operator-54fb85ff56-ks6jl container [manager] '
                                          'restart_count [6]').to_dict(),
    UnhealthyResult(Oracle.SYSTEM_HEALTH, 'deployment: rfs-test-cluster condition [Progressing] status '
                                          '[False] message [ReplicaSet "rfs-test-cluster-5dfc5484bb" has '
                                          'timed out progressing.]').to_dict(),
    UnhealthyResult(Oracle.SYSTEM_HEALTH, 'statefulset: test-cluster-server replicas [3] ready_replicas [2]\n'
                                          'pod: test-cluster-server-2').to_dict(),
])))
def test_check(test_case_id, result_dict):
    snapshot = load_snapshot("health", test_case_id)
    oracle_result = checker_func(snapshot)
    assert oracle_result.to_dict() == result_dict
