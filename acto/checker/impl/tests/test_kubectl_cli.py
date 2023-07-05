import pytest

from acto.checker.impl.kubectl_cli import KubectlCliChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import OracleResult, UnchangedInputResult, PassResult
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = KubectlCliChecker()


def checker_func(s: Snapshot, s_prev: Snapshot) -> OracleResult:
    assert s.input != {}
    assert s_prev.input != {}
    assert s.cli_result != {}
    return checker.check(0, s, s_prev)


@pytest.mark.parametrize("test_case_id,result_dict", list(enumerate([
    {'responsible_field': []},
    UnchangedInputResult().to_dict(),
    PassResult().to_dict(),
])))
def test_check(test_case_id, result_dict):
    snapshot = load_snapshot("kubectl_cli", test_case_id)
    snapshot_prev = load_snapshot("kubectl_cli", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result.to_dict() == result_dict
