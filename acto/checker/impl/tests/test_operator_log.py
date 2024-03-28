from typing import Optional

import pytest

from acto.checker.impl.operator_log import OperatorLogChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import PropertyPath
from acto.result import InvalidInputResult
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = OperatorLogChecker()


def checker_func(s: Snapshot, prev_s: Snapshot) -> Optional[InvalidInputResult]:
    """Helper function to check the checker."""
    assert s.operator_log != []
    return checker.check(0, s, prev_s)


@pytest.mark.parametrize(
    "test_case_id,result_dict",
    list(
        enumerate(
            [
                InvalidInputResult(
                    message="StatefulSet.apps \"test-cluster-server\" is invalid: spec.template.spec.restartPolicy: Unsupported value: \"OnFailure\": supported values: \"Always\"",
                    responsible_property=PropertyPath([]),
                ),
                None,
                InvalidInputResult(
                    message="tidb cluster acto-namespace/test-cluster is not valid and must be fixed first, aggregated error: spec.tidb.volumeName: Invalid value: \"lsgqejeydt\": Can not find volumeName: lsgqejeydt in storageVolumes or additionalVolumes/additionalVolumeMounts",
                    responsible_property=PropertyPath([]),
                ),
                InvalidInputResult(
                    message="github.com/rabbitmq/cluster-operator/controllers.(*RabbitmqClusterReconciler).Reconcile\n\t/workspace/controllers/rabbitmqcluster_controller.go:260\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).reconcileHandler\n\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:298\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).processNextWorkItem\n\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:253\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).Start.func2.2\n\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:214",
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
def test_operator_log_checker(test_case_id, result_dict):
    """Test operator log checker."""
    snapshot = load_snapshot("operator_log", test_case_id)
    snapshot_prev = load_snapshot("operator_log", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result == result_dict
