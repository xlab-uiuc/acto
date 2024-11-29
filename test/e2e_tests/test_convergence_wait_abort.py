"""This module tests quick abort from waiting for system convergence upon observing unresolvable 
errors from K8s events when deploying a testcase"""

import logging
import os
import pathlib
from typing import Callable
import tempfile
import unittest
from acto import utils
from acto.kubernetes_engine.kind import Kind
from acto.utils.k8s_event_watcher import k8s_event_watcher_config
from acto.runner import Runner

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestConvergenceWaitAbort(unittest.TestCase):
    """tests if K8sEventWatcher correctly issues abort request by examing log output"""

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        # lower threshold for the sake of faster test
        k8s_event_watcher_config["default_threshold"] = 2

    def test_unsatisfiable_affinity_rule(self):
        """should issue abort when affinity cannot be satisfied"""

        def log_file_test(log_file_path) -> bool:
            keyword = "Aborting convergence wait due to failed predicate (reason: FailedScheduling,"
            with open(log_file_path, "r", encoding="utf-8") as log_file:
                for log_line in log_file:
                    if keyword in log_line:
                        return True
                return False

        resource_manifest_path = os.path.join(
            test_data_dir, "k8s-event-watcher", "unsatisfiable-affinity.yaml"
        )
        self._test_convergence_wait_abort(
            "unsatisfiable-affinity", resource_manifest_path, log_file_test
        )

    def test_invalid_image(self):
        """should abort when detecting image pull errors"""
        def log_file_test(log_file_path) -> bool:
            keyword = "Aborting convergence wait due to failed predicate (reason: Failed,"
            with open(log_file_path, "r", encoding="utf-8") as log_file:
                for log_line in log_file:
                    if keyword in log_line:
                        return True
                return False

        resource_manifest_path = os.path.join(
            test_data_dir, "k8s-event-watcher", "invalid-image.yaml"
        )
        self._test_convergence_wait_abort(
            "invalid-image", resource_manifest_path, log_file_test
        )

    def test_satisfiable_deployment(self):
        "should never abort a convergence wait for satisfiable deployments"
        def log_file_test(log_file_path) -> bool:
            keyword = "Aborting convergence"
            with open(log_file_path, "r", encoding="utf-8") as log_file:
                for log_line in log_file:
                    if keyword in log_line:
                        return False
                return True

        resource_manifest_path = os.path.join(
            test_data_dir, "k8s-event-watcher", "satisfiable-deployment.yaml"
        )
        self._test_convergence_wait_abort(
            "satisfiable", resource_manifest_path, log_file_test
        )


    def _test_convergence_wait_abort(
        self,
        cluster_name: str,
        resource_file_path: str,
        log_test_predicate: Callable[[str], bool],
    ) -> str:
        """apply a resource manifest and examine the log file"""

        tmp_dir = tempfile.TemporaryDirectory()

        log_file_path = os.path.join(tmp_dir.name, "test.log")

        logging.basicConfig(
            filename=log_file_path,
            level=logging.WARN,
            format="%(message)s",
            force=True,
        )

        kube_config_path = os.path.join(
            os.path.expanduser("~"), ".kube/test-" + cluster_name
        )

        cluster = Kind(acto_namespace=0, num_nodes=3, version="v1.27.3")

        cluster.create_cluster(cluster_name, kube_config_path)

        runner = Runner(
            context={
                "namespace": "test",
                "crd": None,
                "preload_images": set(),
            },
            trial_dir=tmp_dir.name,
            kubeconfig=kube_config_path,
            context_name="kind-" + cluster_name,
        )

        utils.create_namespace(runner.apiclient, "test")

        runner.run_without_collect(resource_file_path)
        cluster.delete_cluster(cluster_name, kube_config_path)

        assert log_test_predicate(log_file_path)
        tmp_dir.cleanup()
