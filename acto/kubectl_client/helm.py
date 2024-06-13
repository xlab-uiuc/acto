import subprocess
from typing import Optional


class Helm:
    """Helm client class"""

    def __init__(self, kubeconfig: str, context_name: str) -> None:
        self.kubeconfig = kubeconfig
        self.context_name = context_name

    def helm(self, args: list) -> subprocess.CompletedProcess:
        """Executes a helm command"""
        cmd = ["helm"]
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def repo_add(self, name: str, url: str) -> subprocess.CompletedProcess:
        """Adds a helm repository"""
        cmd = ["repo", "add", name, url]
        return self.helm(cmd)

    def install(
        self,
        release_name: str,
        chart: str,
        namespace: str,
        repo: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Installs a helm chart"""
        cmd = [
            "install",
            release_name,
            chart,
            "--namespace",
            namespace,
            "--create-namespace",
        ]
        if repo:
            cmd.extend(["--repo", repo])
        return self.helm(cmd)
