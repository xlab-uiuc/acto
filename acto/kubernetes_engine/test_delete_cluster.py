import subprocess
from unittest.mock import patch

import pytest

from acto.kubernetes_engine.base import run_delete_command


@patch("acto.kubernetes_engine.base.time.sleep")
@patch("acto.kubernetes_engine.base.subprocess.run")
def test_run_delete_command_raises_after_three_failures(mock_run, mock_sleep):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["kind", "delete", "cluster"], returncode=1
    )

    with pytest.raises(RuntimeError, match="Failed to delete cluster"):
        run_delete_command(["kind", "delete", "cluster"], "acto-test")

    assert mock_run.call_count == 3
    assert mock_sleep.call_count == 2


@patch("acto.kubernetes_engine.base.time.sleep")
@patch("acto.kubernetes_engine.base.subprocess.run")
def test_run_delete_command_succeeds_on_retry(mock_run, mock_sleep):
    mock_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=1),
        subprocess.CompletedProcess(args=[], returncode=0),
    ]

    run_delete_command(["kind", "delete", "cluster"], "acto-test")

    assert mock_run.call_count == 2
    mock_sleep.assert_called_once()
