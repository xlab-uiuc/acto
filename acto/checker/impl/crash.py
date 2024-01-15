from typing import Optional

from acto.checker.checker import CheckerInterface
from acto.lib.dict import visit_dict
from acto.result import OracleResult
from acto.snapshot import Snapshot


def check_pod_status(pod):
    container_statuses = pod["status"]["container_statuses"]
    pod_name = pod["metadata"]["name"]
    if not container_statuses:
        return
    for container_status in container_statuses:
        if "state" not in container_status:
            continue
        if visit_dict(container_status["state"], ["terminated", "reason"]) == (
            True,
            "Error",
        ):
            return OracleResult(message=f"Pod {pod_name} crashed")
        if visit_dict(container_status["state"], ["waiting", "reason"]) == (
            True,
            "CrashLoopBackOff",
        ):
            return OracleResult(message=f"Pod {pod_name} crashed")

    return None


class CrashChecker(CheckerInterface):
    name = "crash"

    def check(
        self, _: int, snapshot: Snapshot, __: Snapshot
    ) -> Optional[OracleResult]:
        pods = snapshot.system_state["pod"]
        deployment_pods = snapshot.system_state["deployment_pods"]

        for _, pod in pods.items():
            if (result := check_pod_status(pod)) is not None:
                return result

        for _, deployment in deployment_pods.items():
            for pod in deployment:
                if (result := check_pod_status(pod)) is not None:
                    return result

        return None
