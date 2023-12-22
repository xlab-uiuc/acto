"""This module contains the check functions for the performance measurement plugin."""
import logging
from typing import List

import kubernetes
import kubernetes.client.models as k8s_models


def check_resources(
    desired_resources: dict, sts_object: k8s_models.V1StatefulSet
) -> bool:
    """Check if resources match"""
    if desired_resources is not None:
        resource_matched = True
        if "limits" in desired_resources and desired_resources["limits"]:
            if (
                "limits"
                not in sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]
                or not sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]["limits"]
            ):
                resource_matched = False
            else:
                for resource in desired_resources["limits"]:
                    if (
                        desired_resources["limits"][resource]
                        != sts_object["spec"]["template"]["spec"]["containers"][
                            0
                        ]["resources"]["limits"][resource]
                    ):
                        resource_matched = False
        else:
            if (
                "limits"
                in sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]
                and sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]["limits"]
            ):
                resource_matched = False

        if "requests" in desired_resources and desired_resources["requests"]:
            if (
                "requests"
                not in sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]
                or not sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]["requests"]
            ):
                resource_matched = False
            else:
                for resource in desired_resources["requests"]:
                    if (
                        desired_resources["requests"][resource]
                        != sts_object["spec"]["template"]["spec"]["containers"][
                            0
                        ]["resources"]["requests"][resource]
                    ):
                        resource_matched = False
        else:
            if (
                "requests"
                in sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]
                and sts_object["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ]["requests"]
            ):
                resource_matched = False
        return resource_matched
    else:
        if (
            sts_object["spec"]["template"]["spec"]["containers"][0][
                "resources"
            ]["limits"]
            is not None
        ):
            return False
        if (
            sts_object["spec"]["template"]["spec"]["containers"][0][
                "resources"
            ]["requests"]
            is not None
        ):
            return False
        return True


def check_tolerations(
    desired_tolerations: List[dict], sts_object: k8s_models.V1StatefulSet
) -> bool:
    """Check if tolerations match"""
    if desired_tolerations is None or len(desired_tolerations) == 0:
        return (
            sts_object["spec"]["template"]["spec"]["tolerations"] is None
            or len(sts_object["spec"]["template"]["spec"]["tolerations"]) == 0
        )
    toleration_matched = True
    for toleration in desired_tolerations:
        if sts_object["spec"]["template"]["spec"]["tolerations"] is None:
            toleration_matched = False
            break
        for toleration_in_sts in sts_object["spec"]["template"]["spec"][
            "tolerations"
        ]:
            if (
                (
                    "effect" not in toleration
                    or toleration["effect"] == toleration_in_sts["effect"]
                )
                and (
                    "key" not in toleration
                    or toleration["key"] == toleration_in_sts["key"]
                )
                and (
                    "operator" not in toleration
                    or toleration["operator"] == toleration_in_sts["operator"]
                )
                and (
                    "value" not in toleration
                    or toleration["value"] == toleration_in_sts["value"]
                )
            ):
                break
        else:
            toleration_matched = False
            break

    current_tolerations = sts_object["spec"]["template"]["spec"]["tolerations"]
    if current_tolerations is None:
        return desired_tolerations is None
    for toleration in current_tolerations:
        for toleration_in_sts in desired_tolerations:
            if (
                (
                    "effect" not in toleration
                    or toleration["effect"] == toleration_in_sts["effect"]
                )
                and (
                    "key" not in toleration
                    or toleration["key"] == toleration_in_sts["key"]
                )
                and (
                    "operator" not in toleration
                    or toleration["operator"] == toleration_in_sts["operator"]
                )
                and (
                    "value" not in toleration
                    or "value" not in toleration_in_sts
                    or toleration["value"] == toleration_in_sts["value"]
                )
            ):
                break
            if "value" not in toleration and "value" not in toleration_in_sts:
                break
        else:
            toleration_matched = False
            break

    return toleration_matched


def check_affinity(
    desired_affinity: dict, sts_object: k8s_models.V1StatefulSet
) -> bool:
    """Check if affinity match"""
    current_affinity = sts_object["spec"]["template"]["spec"]["affinity"]
    if desired_affinity is None or len(desired_affinity) == 0:
        return current_affinity is None or len(current_affinity) == 0
    else:
        return current_affinity is not None and len(current_affinity) > 0


def check_persistent_volume_claim_retention_policy(
    desired_policy: dict, sts_object: k8s_models.V1StatefulSet
) -> bool:
    """Check if persistent volume claim retention policy match"""
    current_policy = sts_object["spec"][
        "persistent_volume_claim_retention_policy"
    ]
    if desired_policy is not None:
        if (
            "whenDeleted" in desired_policy
            and desired_policy["whenDeleted"]
            and current_policy["when_deleted"] != desired_policy["whenDeleted"]
        ):
            return False

        if (
            "whenScaled" in desired_policy
            and desired_policy["whenScaled"]
            and current_policy["when_scaled"] != desired_policy["whenScaled"]
        ):
            return False

    return True


def check_pods_ready(
    input_dict: dict, apiclient: kubernetes.client.ApiClient, namespace: str
):
    """Check if pods are ready"""
    core_v1_api = kubernetes.client.CoreV1Api(apiclient)
    app_v1_api = kubernetes.client.AppsV1Api(apiclient)
    statefulsets = app_v1_api.list_namespaced_stateful_set(namespace)
    daemonsets = app_v1_api.list_namespaced_daemon_set(namespace)

    for statefulset in statefulsets.items:
        sts_object = statefulset.to_dict()

        if (
            sts_object["status"]["current_revision"]
            != sts_object["status"]["update_revision"]
        ):
            return False

        if (
            sts_object["status"]["ready_replicas"]
            != input_dict["spec"]["replicas"]
        ):
            return False

    for daemonset in daemonsets.items:
        ds_object = daemonset.to_dict()

        if (
            ds_object["status"]["number_ready"]
            != ds_object["status"]["desired_number_scheduled"]
        ):
            logging.info(
                "Daemonset not ready: %s", ds_object["metadata"]["name"]
            )
            return False

    pods = core_v1_api.list_namespaced_pod(namespace)
    for pod in pods.items:
        pod_object = pod.to_dict()

        if pod_object["status"]["phase"] != "Running":
            logging.info("Pod not running: %s", pod_object["metadata"]["name"])
            return False

        containers_ready = True
        for container_status in pod_object["status"]["container_statuses"]:
            if container_status["ready"] is not True:
                containers_ready = False
                break
        if not containers_ready:
            logging.info(
                "Container not ready: %s", pod_object["metadata"]["name"]
            )
            return False

    return True
