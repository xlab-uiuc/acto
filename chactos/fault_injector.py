import abc

from acto.kubectl_client.helm import Helm


class FaultInjectorInterface(abc.ABC):
    """Interface for fault injectors"""

    def __init__(self) -> None:
        pass


class ChaosMeshFaultInjector(FaultInjectorInterface):
    """Fault injector implemented using Chaos Mesh"""

    def __init__(self) -> None:
        pass

    def install(self, kube_config: str, kube_context: str):
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
            ],
        )

        if p.returncode != 0:
            raise RuntimeError("Failed to install chaos-mesh", p.stderr)
