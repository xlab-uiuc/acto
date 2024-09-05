import yaml

from chactos.failures.failure import Failure


class OperatorApplicationPartitionFailure(Failure):
    """Simulate a network partition between the operator and the application"""

    def __init__(self, operator_selector: dict, app_selector: dict):
        self.operator_selector = operator_selector
        self.app_selector = app_selector

        super().__init__()

    def name(self) -> str:
        """Get the name of the failure"""
        return "operator-application-partition"

    def to_dict(self) -> dict:
        """Dump the spec to a dict"""
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": {
                "name": "operator-application-partition",
            },
            "spec": {
                "action": "partition",
                "mode": "all",
                "selector": self.operator_selector,
                "direction": "both",
                "target": {
                    "mode": "all",
                    "selector": self.app_selector,
                },
            },
        }

    def to_file(self, file_path: str):
        """Write the spec to a file"""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)


class ApplicationMinorityFailure(Failure):
    """Simulate a network failure in the application"""

    def __init__(self, pod_prefix: str, total_pods: int, namespace: str):
        self.pod_prefix = pod_prefix
        self.total_pods = total_pods
        self.namespace = namespace

        super().__init__()

    def name(self) -> str:
        """Get the name of the failure"""
        return "application-failure"

    def to_dict(self) -> dict:
        """Dump the spec to a dict"""
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": {
                "name": "application-failure",
            },
            "spec": {
                "action": "partition",
                "mode": "all",
                "selector": {
                    "pods": {
                        self.namespace: [
                            f"{self.pod_prefix}-{i}"
                            for i in range(0, self.total_pods // 2)
                        ]
                    }
                },
                "direction": "both",
            },
        }

    def to_file(self, file_path: str):
        """Write the spec to a file"""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)
