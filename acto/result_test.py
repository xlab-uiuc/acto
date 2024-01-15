import pytest

from acto.checker.impl.tests import load_snapshot
from acto.result import CliStatus, check_kubectl_cli


@pytest.mark.parametrize(
    "test_case_id,result_dict",
    list(
        enumerate(
            [
                CliStatus.INVALID,
                CliStatus.UNCHANGED,
                CliStatus.PASS,
            ]
        )
    ),
)
def test_check_kubectl_cli(test_case_id, result_dict):
    """Test check_kubectl_cli"""
    snapshot = load_snapshot("kubectl_cli", test_case_id)
    oracle_result = check_kubectl_cli(snapshot)
    assert oracle_result == result_dict
