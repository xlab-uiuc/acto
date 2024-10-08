import json
import subprocess
import sys
from typing import Optional

import kubernetes
import kubernetes.client.models as k8s_models
import yaml

from acto.kubectl_client import KubectlClient

from .thread_logger import get_thread_logger


def get_existing_images(worker_list: list[str]) -> set[str]:
    """Get existing images from pods"""
    existing_images = set()
    for worker in worker_list:
        p = subprocess.run(
            [
                "docker",
                "exec",
                worker,
                "crictl",
                "images",
                "--digests",
                "--no-trunc",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        output = p.stdout.strip()
        for line in output.split("\n")[1:]:
            items = line.split()
            if "none" not in items[1]:
                image = f"{items[0]}:{items[1]}"
                existing_images.add(image)
    return existing_images


def process_crd(
    apiclient: kubernetes.client.ApiClient,
    kubectl_client: KubectlClient,
    crd_name: Optional[str] = None,
    crd_version: Optional[str] = None,
    helper_crd: Optional[str] = None,
) -> dict:
    """Get crd from k8s and set context['crd']

    Args:
        apiclient: k8s api client
        kubectl_client: kubectl client
        crd_name: name of the crd
        helper_crd: helper crd file path

    Returns:
        crd_data: crd dict

    When there are more than one crd in the cluster, user should set crd_name
    """
    logger = get_thread_logger(with_prefix=False)

    if helper_crd is None:
        apiextensions_v1_api = kubernetes.client.ApiextensionsV1Api(apiclient)
        crds: list[k8s_models.V1CustomResourceDefinition] = (
            apiextensions_v1_api.list_custom_resource_definition().items
        )
        crd: Optional[k8s_models.V1CustomResourceDefinition] = None
        if len(crds) == 0:
            logger.error("No crd is found")
            sys.exit(1)
        elif len(crds) == 1:
            crd = crds[0]
        elif crd_name:
            for c in crds:
                if c.metadata.name == crd_name:
                    crd = c
                    break
            if not crd:
                logger.error("Cannot find crd %s", crd_name)
                sys.exit(1)
        else:
            logger.error(
                "There are multiple crds, please specify parameter [crd_name]"
            )
            sys.exit(1)
        if crd:
            # there is openAPIV3Schema schema issue when using python k8s client,
            # need to fetch data from cli
            crd_result = kubectl_client.kubectl(
                ["get", "crd", crd.metadata.name, "-o", "json"], True, True
            )
            crd_obj = json.loads(crd_result.stdout)
            spec: k8s_models.V1CustomResourceDefinitionSpec = crd.spec
            crd_data = {
                "group": spec.group,
                "plural": spec.names.plural,
                "version": (
                    spec.versions[-1].name
                    if crd_version is None
                    else crd_version
                ),
                "body": crd_obj,
            }
            return crd_data
        else:
            logger.error("Cannot find crd %s", crd_name)
            sys.exit(1)
    else:
        with open(helper_crd, "r", encoding="utf-8") as helper_crd_f:
            helper_crd_docs = list(yaml.safe_load_all(helper_crd_f))


        if crd_name:
            for doc in helper_crd_docs:
                if doc["metadata"]["name"] == crd_name:
                    helper_crd_doc = doc
                    break
        else:
            helper_crd_doc = helper_crd_docs[0]
        
        crd_data = {
            "group": helper_crd_doc["spec"]["group"],
            "plural": helper_crd_doc["spec"]["names"]["plural"],
            "version": (
                helper_crd_doc["spec"]["versions"][-1]["name"]
                if crd_version is None
                else crd_version
            ),
            "body": helper_crd_doc,
        }
        return crd_data


def add_acto_label(apiclient: kubernetes.client.ApiClient, namespace: str):
    """Add acto label to deployment, stateful_state and corresponding pods."""
    app_v1_api = kubernetes.client.AppsV1Api(apiclient)
    operator_deployments = app_v1_api.list_namespaced_deployment(
        namespace, watch=False
    ).items
    operator_stateful_states = app_v1_api.list_namespaced_stateful_set(
        namespace, watch=False
    ).items
    for deployment in operator_deployments:
        patches = [
            {"metadata": {"labels": {"acto/tag": "operator-deployment"}}},
            {
                "spec": {
                    "template": {
                        "metadata": {"labels": {"acto/tag": "operator-pod"}}
                    }
                }
            },
        ]
        for patch in patches:
            app_v1_api.patch_namespaced_deployment(
                deployment.metadata.name, deployment.metadata.namespace, patch
            )
    for stateful_state in operator_stateful_states:
        patches = [
            {"metadata": {"labels": {"acto/tag": "operator-stateful-set"}}},
            {
                "spec": {
                    "template": {
                        "metadata": {"labels": {"acto/tag": "operator-pod"}}
                    }
                }
            },
        ]
        for patch in patches:
            app_v1_api.patch_namespaced_stateful_set(
                stateful_state.metadata.name,
                stateful_state.metadata.namespace,
                patch,
            )
