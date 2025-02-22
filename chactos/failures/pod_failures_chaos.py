import json
import math
from typing import Optional

import kubernetes
import yaml
from typing_extensions import Self

from chactos.failures.failure import Failure


def build_label_selector(label_selector: dict) -> str:
    """Build a label selector from a dict"""
    return ",".join([f"{key}={value}" for key, value in label_selector.items()])


def select_pods(
    priority_pods: set[str], normal_pods: set[str], number: int
) -> list[str]:
    """Select a number of pods from the list of pods"""
    selected_pods = []
    for _ in range(number):
        if len(priority_pods) > 0:
            pod = priority_pods.pop()
            normal_pods.discard(pod)
        else:
            pod = normal_pods.pop()
        selected_pods.append(pod)
    return selected_pods


class PodFailure(Failure):
    """Simulates a pod crash failure in the cluster"""

    def __init__(
        self,
        selector: dict,
        namespace: str,
    ):
        self._selector = selector
        self._namespace = namespace

        super().__init__()

    def name(self) -> str:
        """Get the name of the failure

        The name is unique by hashing on the tuple of the selector and namespace
        """
        h = hash((json.dumps(self._selector, sort_keys=True), self._namespace))
        return f"pod-crash-failure-{h}"

    @classmethod
    def build_from_api(
        cls,
        api_client: kubernetes.client.ApiClient,
        namespace: str,
        pod_selector: dict,
        failure_ratio: float = 1.0,
        priority_pod_selector: Optional[dict] = None,
    ) -> Self:
        """Build a PodFailure dynamically from the Kubernetes API"""

        # We need to dynamically select pods to inject faults
        # Selecting pods to inject faults
        priority_pod_names = set()
        normal_pod_names = set()
        core_v1_api = kubernetes.client.CoreV1Api(api_client)

        if priority_pod_selector is not None:
            # TODO: only support labelSelector right now
            priority_label_selector = build_label_selector(
                priority_pod_selector["labelSelectors"]
            )
            priority_pods = core_v1_api.list_namespaced_pod(
                namespace=namespace,
                watch=False,
                label_selector=priority_label_selector,
            ).items

            for pod in priority_pods:
                priority_pod_names.add(pod.metadata.name)

        normal_selection_label = build_label_selector(
            pod_selector["labelSelectors"]
        )
        normal_pods = core_v1_api.list_namespaced_pod(
            namespace=namespace,
            watch=False,
            label_selector=normal_selection_label,
        ).items
        for pod in normal_pods:
            normal_pod_names.add(pod.metadata.name)
        num_total_pods = len(priority_pod_names | normal_pod_names)
        num_pods_to_fail = math.ceil(num_total_pods * failure_ratio)
        selected_pods = select_pods(
            priority_pod_names,
            normal_pod_names,
            num_pods_to_fail,
        )

        return cls(
            selector={
                "pods": {namespace: selected_pods},
                "namespaces": [namespace],
            },
            namespace=namespace,
        )

    def to_dict(self) -> dict:
        """Dump the spec to a dict"""
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "PodChaos",
            "metadata": {
                "name": self.name(),
            },
            "spec": {
                "action": "pod-failure",
                "mode": "all",
                "duration": "30s",
                "selector": self._selector,
            },
        }

    def to_file(self, file_path: str):
        """Write the spec to a file"""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)
