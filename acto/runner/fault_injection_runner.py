"""Runner module for Acto"""

import logging
from typing import Callable

import kubernetes

from acto.common import kubernetes_client
from acto.kubectl_client import KubectlClient
from acto.snapshot import Snapshot

RunnerHookType = Callable[[kubernetes.client.ApiClient], None]
CustomSystemStateHookType = Callable[
    [kubernetes.client.ApiClient, str, int], dict
]


class FaultInjectionRunner:
    """Runner class for Acto.
    This class is used to run the cmd and collect system state,
    delta, operator log, events and input files.
    """

    def __init__(
        self,
        trial_dir: str,
        kubeconfig: str,
        context_name: str,
    ):
        self.trial_dir = trial_dir
        self.kubeconfig = kubeconfig
        self.context_name = context_name

        self.kubectl_client = KubectlClient(kubeconfig, context_name)

        apiclient = kubernetes_client(kubeconfig, context_name)

    def run(
        self,
        file_path: str,
        namespace: str,
    ) -> tuple[Snapshot, bool]:
        """Apply the input CR"""

        cmd = ["apply", "-f", file_path, "-n", namespace]

        # submit the CR
        cli_result = self.kubectl_client.kubectl(
            cmd, capture_output=True, text=True
        )

        if cli_result.returncode != 0:
            logging.error(
                "kubectl apply failed with return code %d",
                cli_result.returncode,
            )
            logging.error("STDOUT: %s", cli_result.stdout)
            logging.error("STDERR: %s", cli_result.stderr)
