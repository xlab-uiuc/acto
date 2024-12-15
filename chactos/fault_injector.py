import abc
import os

from acto.common import kubernetes_client
from acto.kubectl_client.helm import Helm
from acto.system_state.kubernetes_system_state import KubernetesSystemState
from acto.utils import thread_logger


class FaultInjectorInterface(abc.ABC):
    """Interface for fault injectors"""

    def __init__(self) -> None:
        pass


class ChaosMeshFaultInjector(FaultInjectorInterface):
    """Fault injector implemented using Chaos Mesh"""

    def __init__(self) -> None:
        pass

    def install(self, kube_config: str, kube_context: str) -> bool:
        """install chaos-mesh"""
        helm_client = Helm(kube_config, kube_context)
        p = helm_client.install(
            release_name="chaos-mesh",
            chart="chaos-mesh",
            namespace="chaos-mesh",
            repo="https://charts.chaos-mesh.org",
            namespace_existed=False,
            args=[
                "--set",
                "chaosDaemon.runtime=containerd",
                "--set",
                "chaosDaemon.socketPath=/run/containerd/containerd.sock",
                "--version",
                "2.7.0",
                "--atomic",
            ],
        )

        if p.returncode != 0:
            thread_logger.get_thread_logger().error(
                "Failed to install chaos-mesh: %s", p.stderr
            )
            return False
        return True

    def install_with_retry(
        self, kube_config: str, kube_context: str, retry: int = 3
    ) -> None:
        """install chaos-mesh with retry"""
        for _ in range(retry):
            if self.install(kube_config, kube_context):
                return
        system_state = KubernetesSystemState.from_api_client(
            api_client=kubernetes_client(kube_config, kube_context),
            namespace="chaos-mesh",
        )
        system_state.dump(os.path.join(".", "chaos_failed_system_state.json"))
        raise RuntimeError("Failed to install chaos-mesh")
