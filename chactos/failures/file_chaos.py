from chactos.failures.failure import Failure


class ApplicationFileFailure(Failure):
    """Simulate a file failure in the application"""

    def __init__(self, app_selector: dict):
        self.app_selector = app_selector

        super().__init__()

    def name(self) -> str:
        return "application-file-failure"

    def to_dict(self) -> dict:
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "IOChaos",
            "metadata": {
                "name": "application-file-failure",
            },
            "spec": {
                "action": "fault",
                "mode": "all",
                "selector": self.app_selector,
                "volumePath": "/data/db",
                "errno": 5,
                "duration": "600s",
            },
        }


class ApplicationFileDelay(Failure):
    """Simulate a file delay in the application"""

    def __init__(self, app_selector: dict):
        self.app_selector = app_selector

        super().__init__()

    def name(self) -> str:
        return "application-file-delay"

    def to_dict(self) -> dict:
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "IOChaos",
            "metadata": {
                "name": "application-file-delay",
            },
            "spec": {
                "action": "latency",
                "mode": "all",
                "selector": self.app_selector,
                "volumePath": "/data/db",
                "delay": "2s",
                "duration": "600s",
            },
        }
