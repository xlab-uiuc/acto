import datetime
from typing import Optional

import kubernetes

# pylint: disable=import-error
from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger

# pylint: enable=import-error

VREPLICASET_GROUP = "anvil.dev"
VREPLICASET_VERSION = "v1"
VREPLICASET_PLURAL = "vreplicasets"


class VDeploymentChecker(CheckerInterface):
    """Custom oracle for checking VDeployment config"""

    name = "vdeployment-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle
        self._previous_ts: Optional[datetime.datetime] = None

    def __get_owned_vreplicasets(self, vdeployment_name: str) -> list[dict]:
        """List VReplicaSets in the namespace owned by the given VDeployment."""
        custom_api = kubernetes.client.CustomObjectsApi(
            self.oracle_handle.k8s_client
        )
        vrs_list = custom_api.list_namespaced_custom_object(
            group=VREPLICASET_GROUP,
            version=VREPLICASET_VERSION,
            namespace=self.oracle_handle.namespace,
            plural=VREPLICASET_PLURAL,
        )
        owned = []
        for vrs in vrs_list.get("items", []):
            owner_refs = vrs.get("metadata", {}).get("ownerReferences") or []
            for ref in owner_refs:
                if (
                    ref.get("kind") == "VDeployment"
                    and ref.get("name") == vdeployment_name
                ):
                    owned.append(vrs)
                    break
        return owned

    def __check_spec(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check that the VReplicaSet spec matches the VDeployment spec."""
        _, _ = generation, prev_snapshot
        logger = get_thread_logger()

        input_cr = snapshot.input_cr
        vd_name = input_cr.get("metadata", {}).get("name", "")
        vd_spec = input_cr.get("spec", {})

        vrs_list = self.__get_owned_vreplicasets(vd_name)
        if not vrs_list:
            logger.error(
                "No VReplicaSet found owned by VDeployment %s", vd_name
            )
            return OracleResult(
                message=f"No VReplicaSet found owned by VDeployment {vd_name!r}"
            )

        # Use the most recently created VReplicaSet (current revision)
        vrs = vrs_list[-1]
        vrs_spec = vrs.get("spec", {})

        desired_replicas = vd_spec.get("replicas")
        actual_replicas = vrs_spec.get("replicas")
        if desired_replicas is not None and actual_replicas != desired_replicas:
            return OracleResult(
                message=(
                    f"VReplicaSet replicas mismatch: expected {desired_replicas}, "
                    f"got {actual_replicas}"
                )
            )

        vd_selector = vd_spec.get("selector")
        vrs_selector = vrs_spec.get("selector")
        if vd_selector is not None and vrs_selector != vd_selector:
            return OracleResult(
                message=(
                    f"VReplicaSet selector mismatch: expected {vd_selector}, "
                    f"got {vrs_selector}"
                )
            )

        vd_template = vd_spec.get("template")
        vrs_template = vrs_spec.get("template")
        if vd_template is not None and vrs_template != vd_template:
            return OracleResult(
                message=(
                    f"VReplicaSet template mismatch: expected {vd_template}, "
                    f"got {vrs_template}"
                )
            )

        return None

    def __check_health(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check that the VReplicaSet's pods are ready using the snapshot system state."""
        _, _ = generation, prev_snapshot
        logger = get_thread_logger()

        input_cr = snapshot.input_cr
        vd_name = input_cr.get("metadata", {}).get("name", "")
        desired_replicas = input_cr.get("spec", {}).get("replicas", 1)

        deployment_pods = snapshot.system_state.get("deployment_pods", {})
        pods = deployment_pods.get(vd_name, [])

        if not pods and desired_replicas > 0:
            logger.error(
                "No pods found for VDeployment %s in deployment_pods", vd_name
            )
            return OracleResult(
                message=f"No pods found for VDeployment {vd_name!r} in deployment_pods"
            )

        ready_count = sum(
            1
            for pod in pods
            if pod.get("status", {}).get("conditions")
            and any(
                c.get("type") == "Ready" and c.get("status") == "True"
                for c in pod["status"]["conditions"]
            )
        )

        logger.info(
            "VReplicaSet health: %d/%d pods ready",
            ready_count,
            desired_replicas,
        )

        if ready_count < desired_replicas:
            return OracleResult(
                message=(
                    f"VReplicaSet health check failed: "
                    f"{ready_count}/{desired_replicas} pods ready"
                )
            )

        return None

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the VDeployment config and availability"""
        logger = get_thread_logger()
        logger.info("Checking VDeployment config")

        if result := self.__check_spec(generation, snapshot, prev_snapshot):
            return result
        if result := self.__check_health(generation, snapshot, prev_snapshot):
            return result
        return None


CUSTOM_CHECKER: type[CheckerInterface] = VDeploymentChecker
