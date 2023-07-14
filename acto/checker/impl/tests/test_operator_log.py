import pytest

from acto.checker.impl.operator_log import OperatorLogChecker, OperatorLogResult
from acto.checker.impl.tests import load_snapshot
from acto.checker.checker import OracleResult, OracleControlFlow
from acto.snapshot import Snapshot

# Crash checker is stateless, so we can use the same instance for all tests
checker = OperatorLogChecker()


def checker_func(s: Snapshot, prev_s: Snapshot) -> OracleResult:
    assert s.operator_log != []
    return checker.check(s, prev_s)


@pytest.mark.parametrize("test_case_id,expected", list(enumerate([
    (OperatorLogResult(message='Operator log contains error message: '
                               '{"level":"error","ts":1686059726.1682673,"logger":"controller-runtime.manager.controller.rabbitmqcluster","msg":"failed '
                               'to  resource test-cluster-server of Type '
                               '*v1.StatefulSet","reconciler '
                               'group":"rabbitmq.com","reconciler '
                               'kind":"RabbitmqCluster","name":"test-cluster","namespace":"rabbitmq-system","error":"StatefulSet.apps '
                               '\\"test-cluster-server\\" is invalid: '
                               'spec.template.spec.restartPolicy: Unsupported '
                               'value: \\"OnFailure\\": supported values: '
                               '\\"Always\\"","stacktrace":"github.com/rabbitmq/cluster-operator/controllers.(*RabbitmqClusterReconciler).Reconcile\\n\\t/workspace/controllers/rabbitmqcluster_controller.go:225\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).reconcileHandler\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:298\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).processNextWorkItem\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:253\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).Start.func2.2\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:214"}',
                       invalid_field_path=[]), OracleControlFlow.revert),
    (OperatorLogResult(), OracleControlFlow.ok),
    (OperatorLogResult(message='Operator log contains error message: E0716 '
                               '04:06:24.911615       1 '
                               'tidb_cluster_control.go:129] tidb cluster '
                               'acto-namespace/test-cluster is not valid and must '
                               'be fixed first, aggregated error: '
                               'spec.tidb.volumeName: Invalid value: "lsgqejeydt": '
                               'Can not find volumeName: lsgqejeydt in '
                               'storageVolumes or '
                               'additionalVolumes/additionalVolumeMounts',
                       invalid_field_path=[]
                       ), OracleControlFlow.revert),
    (OperatorLogResult(message='Operator log contains error message: '
                               '{"level":"error","ts":1688507446.4684289,"logger":"controller-runtime.manager.controller.rabbitmqcluster","msg":"Failed '
                               'to update Custom Resource status","reconciler '
                               'group":"rabbitmq.com","reconciler '
                               'kind":"RabbitmqCluster","name":"test-cluster","namespace":"rabbitmq-system","namespace":"rabbitmq-system","name":"test-cluster","error":"Operation '
                               'cannot be fulfilled on '
                               'rabbitmqclusters.rabbitmq.com \\"test-cluster\\": '
                               'the object has been modified; please apply your '
                               'changes to the latest version and try '
                               'again","stacktrace":"github.com/rabbitmq/cluster-operator/controllers.(*RabbitmqClusterReconciler).Reconcile\\n\\t/workspace/controllers/rabbitmqcluster_controller.go:260\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).reconcileHandler\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:298\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).processNextWorkItem\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:253\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).Start.func2.2\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:214"}',
                       invalid_field_path=['spec',
                                           'affinity',
                                           'podAntiAffinity',
                                           'requiredDuringSchedulingIgnoredDuringExecution',
                                           0,
                                           'labelSelector',
                                           'matchExpressions',
                                           0,
                                           'operator'],
                       ), OracleControlFlow.revert),
])))
def test_check(test_case_id, expected):
    expected, expected_control_flow = expected
    expected.emit_by = "log"
    snapshot = load_snapshot("operator_log", test_case_id)
    snapshot_prev = load_snapshot("operator_log", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result == expected
    for control_flow in OracleControlFlow:
        if control_flow == expected_control_flow:
            assert expected.means(control_flow)
        else:
            assert not expected.means(control_flow)
