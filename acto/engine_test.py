"""Tests for the trial runner's handling of operator deploy failures"""

import tempfile
import unittest
from unittest import mock

from acto import engine


def make_runner(deploy_results: list, workdir: str) -> engine.TrialRunner:
    """Make a TrialRunner whose operator deploy returns the given results"""
    deploy = mock.Mock()
    deploy.deploy_with_retry.side_effect = deploy_results
    input_model = mock.Mock()
    input_model.is_empty.return_value = False
    return engine.TrialRunner(
        context={"namespace": "acto-test"},
        input_model=input_model,
        deploy=deploy,
        runner_t=mock.Mock(),
        checker_t=mock.Mock(),
        wait_time=0,
        custom_on_init=None,
        custom_checker=None,
        custom_runner_hooks=None,
        workdir=workdir,
        cluster=mock.Mock(get_context_name=lambda name: f"kind-{name}"),
        worker_id=0,
        sequence_base=0,
        dryrun=False,
        is_reproduce=False,
        apply_testcase_f=mock.Mock(),
        acto_namespace=0,
        images_archive="/nonexistent.tar",
    )


@mock.patch.object(engine, "KubectlClient", mock.Mock())
@mock.patch.object(engine, "kubernetes_client", mock.Mock())
class TestTrialRunnerDeployFailure(unittest.TestCase):
    """Test TrialRunner.run when the operator cannot be deployed"""

    def test_persistent_deploy_failure_stops_worker(self):
        """A worker gives up instead of restarting the cluster forever"""
        runner = make_runner([False] * 50, "/nonexistent")
        with self.assertRaises(RuntimeError):
            runner.run([])
        limit = engine.MAX_CONSECUTIVE_DEPLOY_FAILURES
        self.assertEqual(runner.cluster.restart_cluster.call_count, limit)
        self.assertEqual(runner.deploy.deploy_with_retry.call_count, limit)

    @mock.patch.object(engine, "delete_operator_pod", mock.Mock())
    def test_deploy_success_resets_failure_count(self):
        """Failures that are not consecutive do not stop the worker"""
        with tempfile.TemporaryDirectory() as workdir:
            runner = make_runner([False, False, True] * 2, workdir)
            runner.run_trial = mock.Mock()
            runner.input_model.is_empty.side_effect = (
                lambda: runner.run_trial.call_count >= 2
            )
            runner.run([])
        self.assertEqual(runner.run_trial.call_count, 2)
