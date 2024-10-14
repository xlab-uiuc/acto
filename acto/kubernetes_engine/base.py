import subprocess
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional

import kubernetes

from acto.constant import CONST
from acto.utils import get_thread_logger

KubernetesEnginePostHookType = Callable[[kubernetes.client.ApiClient], None]


class KubernetesEngine(ABC):
    """Interface for KubernetesEngine"""

    @abstractmethod
    def __init__(
        self,
        acto_namespace: int,
        posthooks: Optional[list[KubernetesEnginePostHookType]] = None,
        feature_gates: Optional[dict[str, bool]] = None,
        num_nodes=1,
        version="",
    ) -> None:
        """Constructor for KubernetesEngine

        Args:
            acto_namespace: the namespace of the acto
            posthooks: a list of posthooks to be executed after the cluster is created
            feature_gates: a list of feature gates to be enabled
        """

    @abstractmethod
    def get_context_name(self, cluster_name: str) -> str:
        """Returns the kubecontext based onthe cluster name"""

    @abstractmethod
    def create_cluster(self, name: str, kubeconfig: str):
        """Use subprocess to create cluster
        Args:
            name: name of the cluster
            config: path of the config file for cluster
            version: k8s version
        """

    @abstractmethod
    def load_images(self, images_archive_path: str, name: str):
        """Load image into the cluster
        Args:
            1. Path of the archive image
            2.Name of the cluster
        """

    @abstractmethod
    def delete_cluster(
        self,
        name: str,
        kubeconfig: str,
    ):
        """Delete a cluster
        Args:
            name: name of the cluster
            kubeconfig: path of the config file for cluster
        """

    def restart_cluster(self, name: str, kubeconfig: str):
        """Restart the cluster
        Args:
            name: name of the kind cluster
            kubeconfig: path of the config file for cluster
        """
        logger = get_thread_logger(with_prefix=False)

        retry_count = 3

        while retry_count > 0:
            try:
                self.delete_cluster(name, kubeconfig)
                time.sleep(1)
                self.create_cluster(name, kubeconfig)
                time.sleep(1)
                logger.info("Created cluster")
            except RuntimeError as e:
                logger.warning(
                    "%s happened when restarting cluster, retrying...", e
                )
                retry_count -= 1
                if retry_count == 0:
                    raise e
                continue
            break

    def get_node_list(self, name: str):
        """Fetch the name of worker nodes inside a cluster
        Args:
            1. name: name of the cluster name
        """
        _ = get_thread_logger(with_prefix=False)

        cmd = ["docker", "ps", "--format", "{{.Names}}", "-f"]

        if name is None:
            cmd.append(f"name={CONST.CLUSTER_NAME}")
        else:
            cmd.append(f"name={name}")

        p = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if p.stdout is None or p.stdout == "":
            # no nodes can be found, returning an empty array
            return []
        return p.stdout.strip().split("\n")

    @staticmethod
    def cluster_name(acto_namespace: int, worker_id: int) -> str:
        """Helper function to generate cluster name"""
        return f"acto-{acto_namespace}-cluster-{worker_id}"
