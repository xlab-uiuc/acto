import subprocess
from unittest.mock import patch

import pytest

from acto.kubernetes_engine.k3d import K3D


@patch("acto.kubernetes_engine.k3d.kubernetes.config.load_kube_config")
@patch("acto.kubernetes_engine.k3d.time.sleep")
@patch.object(K3D, "delete_cluster")
@patch("acto.kubernetes_engine.k3d.subprocess.run")
def test_create_cluster_raises_after_three_failures(
    mock_run, mock_delete, mock_sleep, mock_kube
):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["k3d", "cluster", "create"], returncode=1
    )
    engine = K3D()

    with pytest.raises(RuntimeError, match="Failed to create k3d cluster"):
        engine.create_cluster("acto-test", "1.28.0")

    assert mock_run.call_count == 3
    assert mock_delete.call_count == 2
    assert mock_sleep.call_count == 2
    mock_kube.assert_not_called()


@patch("acto.kubernetes_engine.k3d.kubernetes.config.load_kube_config")
@patch("acto.kubernetes_engine.k3d.time.sleep")
@patch.object(K3D, "delete_cluster")
@patch("acto.kubernetes_engine.k3d.subprocess.run")
def test_create_cluster_succeeds_on_retry(
    mock_run, mock_delete, mock_sleep, mock_kube
):
    mock_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=1),
        subprocess.CompletedProcess(args=[], returncode=0),
    ]
    engine = K3D()

    engine.create_cluster("acto-test", "1.28.0")

    assert mock_run.call_count == 2
    mock_delete.assert_called_once()
    mock_sleep.assert_called_once()
    mock_kube.assert_called_once()
