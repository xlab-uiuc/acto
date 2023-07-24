from acto.checker.impl.recovery import RecoveryChecker
from acto.checker.checker import OracleResult
from acto.snapshot import Snapshot


def checker_func(s: Snapshot, expect_s: Snapshot) -> OracleResult:
    checker = RecoveryChecker()
    s.parent = Snapshot()
    s.parent.parent = expect_s
    return checker.check(s)


def test_enable():
    snapshot = Snapshot(trial_state='normal')
    oracle_result = checker_func(snapshot, snapshot)
    assert oracle_result is None
