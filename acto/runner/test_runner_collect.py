from types import SimpleNamespace
from unittest.mock import MagicMock

from acto.runner.runner import Runner


def _runner_with_api(core_v1_api, operator_container_name=None):
    runner = object.__new__(Runner)
    runner.namespace = "test-ns"
    runner.operator_container_name = operator_container_name
    runner.log_length = 0
    runner.core_v1_api = core_v1_api
    return runner


def test_collect_operator_log_empty_pod_list_returns_empty():
    api = MagicMock()
    api.list_namespaced_pod.return_value = SimpleNamespace(items=[])
    runner = _runner_with_api(api)

    assert runner.collect_operator_log() == []
    api.read_namespaced_pod_log.assert_not_called()


def test_collect_not_ready_pods_logs_skips_none_status_and_conditions():
    api = MagicMock()
    api.list_namespaced_pod.return_value = SimpleNamespace(
        items=[
            SimpleNamespace(
                status=None, metadata=SimpleNamespace(name="no-status")
            ),
            SimpleNamespace(
                status=SimpleNamespace(
                    conditions=None,
                    container_statuses=None,
                    init_container_statuses=None,
                ),
                metadata=SimpleNamespace(name="no-conditions"),
            ),
        ]
    )
    runner = _runner_with_api(api)

    assert runner.collect_not_ready_pods_logs() is None
    api.read_namespaced_pod_log.assert_not_called()
