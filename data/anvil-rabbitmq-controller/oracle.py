from typing import Optional

import kubernetes

# pylint: disable=import-error
from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger

# pylint: enable=import-error

VSTATEFULSET_GROUP = "anvil.dev"
VSTATEFULSET_VERSION = "v1"
VSTATEFULSET_PLURAL = "vstatefulsets"


class VStatefulSetChecker(CheckerInterface):
    """Custom oracle for checking VStatefulSet health for RabbitmqCluster"""

    name = "vstatefulset-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle


    def __get_all_vstatefulsets(self) -> list[dict]:
        """List all VStatefulSets in the namespace."""
        custom_api = kubernetes.client.CustomObjectsApi(
            self.oracle_handle.k8s_client
        )
        vsts_list = custom_api.list_namespaced_custom_object(
            group=VSTATEFULSET_GROUP,
            version=VSTATEFULSET_VERSION,
            namespace=self.oracle_handle.namespace,
            plural=VSTATEFULSET_PLURAL,
        )
        return vsts_list.get("items", [])

    def __check_container_health(
        self,
        generation: int,
        snapshot: Snapshot,
        prev_snapshot: Snapshot,
        vsts: dict,
    ) -> Optional[OracleResult]:
        """Check pod count matches desired replicas and all containers are healthy."""
        _, _ = generation, prev_snapshot
        logger = get_thread_logger()

        vsts_name = vsts.get("metadata", {}).get("name", "")
        desired_replicas = vsts.get("spec", {}).get("replicas", 1)

        # Pods owned directly by VStatefulSet appear in system_state["pod"]
        # (keyed by pod name) since group_pods() does not handle VStatefulSet.
        all_pods: dict = snapshot.system_state.get("pod", {})
        owned_pods = [
            pod
            for pod in all_pods.values()
            if any(
                ref.get("name") == vsts_name
                for ref in (
                    pod.get("metadata", {}).get("owner_references") or []
                )
            )
        ]

        logger.info(
            "VStatefulSet %s: %d/%d pods found",
            vsts_name,
            len(owned_pods),
            desired_replicas,
        )

        if len(owned_pods) != desired_replicas:
            return OracleResult(
                message=(
                    f"VStatefulSet {vsts_name!r} pod count mismatch: "
                    f"expected {desired_replicas}, got {len(owned_pods)}"
                )
            )

        unhealthy = []
        for pod in owned_pods:
            pod_name = pod.get("metadata", {}).get("name", "<unknown>")
            container_statuses = (
                pod.get("status", {}).get("container_statuses") or []
            )
            for cs in container_statuses:
                if not cs.get("ready", False):
                    unhealthy.append(
                        f"{pod_name}/{cs.get('name', '<unknown>')}"
                    )

        if unhealthy:
            return OracleResult(
                message=(
                    f"VStatefulSet {vsts_name!r} has unhealthy containers: "
                    + ", ".join(unhealthy)
                )
            )

        return None

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check VStatefulSet health for the RabbitmqCluster CR."""
        logger = get_thread_logger()
        logger.info("Checking VStatefulSet health")

        vsts_list = self.__get_all_vstatefulsets()
        if not vsts_list:
            return OracleResult(message="No VStatefulSet found in namespace")

        for vsts in vsts_list:
            if result := self.__check_container_health(
                generation, snapshot, prev_snapshot, vsts
            ):
                return result

        return None


CUSTOM_CHECKER: type[CheckerInterface] = VStatefulSetChecker
