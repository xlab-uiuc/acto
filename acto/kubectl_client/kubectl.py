import logging
import subprocess


class KubectlClient:
    """Kubectl client class"""

    def __init__(self, kubeconfig: str, context_name: str):

        if not kubeconfig:
            raise ValueError("kubeconfig is required")
        if not context_name:
            raise ValueError("context_name is required")

        self.kubeconfig = kubeconfig
        self.context_name = context_name

    def exec(
        self,
        pod: str,
        namespace: str,
        commands: list,
        capture_output=False,
        text=False,
    ) -> subprocess.CompletedProcess:
        """Executes a command in a pod"""
        cmd = ["exec"]
        cmd.extend([pod])
        cmd.extend(["--namespace", namespace])
        cmd.extend(["--"])
        cmd.extend(commands)

        return self.kubectl(cmd, capture_output, text)

    def kubectl(
        self, args: list, capture_output=False, text=False, timeout: int = 600
    ) -> subprocess.CompletedProcess:
        """Executes a kubectl command"""
        cmd = ["kubectl"]
        cmd.extend(["--kubeconfig", self.kubeconfig])
        cmd.extend(["--context", self.context_name])

        cmd.extend(args)

        logging.info("Running kubectl command: %s", " ".join(cmd))
        p = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
            check=False,
        )
        return p

    def wait(
        self, file: str, for_condition: str, timeout: int = 600
    ) -> subprocess.CompletedProcess:
        """Waits for a condition to be true"""
        cmd = [
            "wait",
            "-f",
            file,
            "--for",
            for_condition,
            "--timeout",
            str(timeout),
        ]
        return self.kubectl(cmd, capture_output=True, text=True)
