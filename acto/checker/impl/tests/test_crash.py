import pytest

from acto.checker.impl.crash import CrashChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import Oracle, OracleResult, PassResult
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = CrashChecker()


def checker_func(s: Snapshot) -> OracleResult:
    assert s.system_state != {}
    return checker.check(0, s, Snapshot({}))


@pytest.mark.parametrize("test_case_id,result_dict", list(enumerate([
    {'oracle': Oracle.CRASH, 'message': 'Pod test-cluster-server-2 crashed'},
    PassResult().to_dict()
])))
def test_check(test_case_id, result_dict):
    snapshot = load_snapshot("crash", test_case_id)
    oracle_result = checker_func(snapshot)
    assert oracle_result.to_dict() == result_dict
