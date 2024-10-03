from chactos.failures.failure import Failure

import yaml

FAILURE_DIR = ".failures"



class PodFailure(Failure):
    """Simulates a pod crash failure in the cluster"""

    def __init__(
        self, app_selector: dict, namespace: str, failure_ratio: float,
    ):
        self.app_selector = app_selector
        self.namespace = namespace
        self.failure_ratio = failure_ratio

        super().__init__()
    
    def name(self) -> str:
        """Get the name of the failure"""
        return "pod-crash-failure"
    
    def to_dict(self) -> dict:
        """Dump the spec to a dict"""
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "PodChaos",
            "metadata": {
                "name": "pod-crash-failure",
                "namespace": "chaos-mesh"
            },
            "spec": {
                "action": "pod-failure",
                "mode": "fixed-percent",
                "value": self.failure_ratio,
                "duration": '30s',
                "selector": {
                    "labelSelectors": self.app_selector
                },        
            } 
        }
    
    def to_file(self, file_path: str):
        """Write the spec to a file"""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)
