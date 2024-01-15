import pytest

from acto.checker.impl.operator_log import OperatorLogChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import PropertyPath
from acto.result import InvalidInputResult, OracleResult
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = OperatorLogChecker()


def checker_func(s: Snapshot, prev_s: Snapshot) -> OracleResult:
    assert s.operator_log != []
    return checker.check(0, s, prev_s)


@pytest.mark.parametrize(
    "test_case_id,result_dict",
    list(
        enumerate(
            [
                InvalidInputResult(
                    message="Found no matching fields for input",
                    responsible_property=PropertyPath([]),
                ),
                None,
                InvalidInputResult(
                    message="Found no matching fields for input",
                    responsible_property=PropertyPath([]),
                ),
                InvalidInputResult(
                    message="Found no matching fields for input",
                    responsible_property=PropertyPath(
                        [
                            "spec",
                            "affinity",
                            "podAntiAffinity",
                            "requiredDuringSchedulingIgnoredDuringExecution",
                            0,
                            "labelSelector",
                            "matchExpressions",
                            0,
                            "operator",
                        ]
                    ),
                ),
            ]
        )
    ),
)
def test_check(test_case_id, result_dict):
    snapshot = load_snapshot("operator_log", test_case_id)
    snapshot_prev = load_snapshot("operator_log", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result == result_dict
