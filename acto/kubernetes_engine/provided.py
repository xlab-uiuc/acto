import logging
import subprocess
from typing import Optional

import kubernetes

from acto.common import kubernetes_client, print_event
from acto.constant import CONST

from . import base


class ProvidedKubernetesEngine(base.KubernetesEngine):
    """KubernetesEngine for user-provided k8s cluster

    Configuration for user-provided k8s cluster is very limited,
    as it is assumed that the user has already set up the cluster.
    Everything needs to be deployed in the ACTO_NAMESPACE to provide the
    necessary isolation.
    """

    def __init__(
        self,
        acto_namespace: int,
        posthooks: Optional[list[base.KubernetesEnginePostHookType]] = None,
        feature_gates: Optional[dict[str, bool]] = None,
        num_nodes: int = 1,
        version: Optional[str] = None,
        provided: Optional[base.SelfProvidedKubernetesConfig] = None,
    ):
        self._posthooks = posthooks

        if feature_gates:
            logging.error("Feature gates are not supported in provided k8s")

        if num_nodes != 1:
            logging.error("num_nodes is not supported in provided k8s")

        if version:
            logging.error("version is not supported in provided k8s")

        if provided is None:
            raise ValueError("Missing configuration for provided k8s")
        self._kube_config = provided.kube_config
        self._kube_context = provided.kube_context

    def get_context_name(self, cluster_name: str) -> str:
        """Returns the kubecontext based on the cluster name
        KIND always adds `kind` before the cluster name
        """
        return self._kube_context

    def create_cluster(self, name: str, kubeconfig: str):
        """Does nothing as the cluster is already created
        Args:
            name: name of the cluster
            config: path of the config file for cluster
            version: k8s version
        """
        print_event("Connecting to a user-provided Kubernetes cluster...")

        try:
            kubernetes.config.load_kube_config(
                config_file=self._kube_config, context=self._kube_context
            )
            apiclient = kubernetes_client(self._kube_config, self._kube_context)
        except Exception as e:
            logging.debug("Incorrect kube config file:")
            with open(self._kube_config, encoding="utf-8") as f:
                logging.debug(f.read())
            raise e

        if self._posthooks:
            for posthook in self._posthooks:
                posthook(apiclient)

    def load_images(self, images_archive_path: str, name: str):
        logging.info("Loading preload images")
        cmd = ["kind", "load", "image-archive"]
        if images_archive_path is None:
            logging.warning(
                "No image to preload, we at least should have operator image"
            )

        if name is not None:
            cmd.extend(["--name", name])
        else:
            logging.error("Missing cluster name for kind load")

        p = subprocess.run(cmd + [images_archive_path], check=False)
        if p.returncode != 0:
            logging.error("Failed to preload images archive")

    def delete_cluster(self, name: str, kubeconfig: str):
        """Cluster deletion via deleting the acto-namespace
        Args:
            name: name of the cluster
            kubeconfig: path of the config file for cluster
            kubecontext: context of the cluster
        """
        logging.info("Deleting cluster %s", name)
        apiclient = kubernetes_client(self._kube_config, self._kube_context)
        core_v1 = kubernetes.client.CoreV1Api(apiclient)
        core_v1.delete_namespace(
            CONST.ACTO_NAMESPACE, propagation_policy="Foreground"
        )

    def get_node_list(self, name: str) -> list[str]:
        """We don't have a way to get the node list for a user-provided cluster
        Args:
            Name of the cluster
        """
        return []
