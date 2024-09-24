import os
import logging
import yaml

from chactos.failures.failure import Failure

from acto.kubectl_client.kubectl import KubectlClient

FAILURE_DIR = ".failures"


class OperatorApplicationPartitionFailure(Failure):
    """Simulate a network partition between the operator and the application"""

    def __init__(
        self, operator_selector: dict, app_selector: dict, namespace: str
    ):
        self.operator_selector = operator_selector
        self.app_selector = app_selector
        self.namespace = namespace

        super().__init__()

    def apply(self, kubectl_client: KubectlClient):
        """Apply the failure to the cluster"""
        logging.info("Applying %s...", self.name())
        failure_file = os.path.join(FAILURE_DIR, self.name() + ".yaml")
        self.to_file(failure_file)
        p = kubectl_client.kubectl(
            ["apply", "-f", failure_file, "-n", self.namespace],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            raise RuntimeError(f"Failed to apply {self.name()}: {p.stderr}")
        p = kubectl_client.wait(
            failure_file,
            'jsonpath={.status.conditions[?(@.type=="AllInjected")].status}=True',
            timeout=600,
            namespace=self.namespace,
        )
        if p.returncode != 0:
            raise RuntimeError(
                f"Failed to wait for {self.name()} failure to be injected: {p.stderr}"
            )
        logging.info("%s failure applied", self.name())

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
