"""Runner for performance measurement"""

import hashlib
import json
import logging
import queue
import time
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from multiprocessing import Process, Queue
from typing import Callable

import jsonpatch
import kubernetes
import kubernetes.client.models as k8s_models
import yaml

from acto.common import kubernetes_client
from acto.kubectl_client.kubectl import KubectlClient
from acto.runner import Runner
from acto.serialization import ActoEncoder
from acto.utils import acto_timer
from acto.utils.thread_logger import get_thread_logger

from .check_utils import (
    check_affinity,
    check_persistent_volume_claim_retention_policy,
    check_pods_ready,
    check_resources,
    check_tolerations,
)

ConditionFuncType = Callable[[dict, kubernetes.client.ApiClient, str], bool]


@dataclass
class MeasurementResult:
    """Schema for measurement result"""

    start_ts: float
    condition_1_ts: float
    condition_2_ts: float


def check_annotations(
    desired_annotations: dict, sts_object: k8s_models.V1StatefulSet
) -> bool:
    """Check if annotations match"""
    annotation_matched = True
    if desired_annotations is not None:
        # check if input annotations are in sts
        for pod_annotation in desired_annotations:
            if (
                pod_annotation
                not in sts_object["spec"]["template"]["metadata"]["annotations"]
            ):
                # annotation is not in sts, but in input
                annotation_matched = False
                logging.info("annotation is not in sts, but in input")
                break
            if (
                sts_object["spec"]["template"]["metadata"]["annotations"][
                    pod_annotation
                ]
                != desired_annotations[pod_annotation]
            ):
                # annotation value not match
                annotation_matched = False
                logging.info("annotation value not match")
                break
        if not annotation_matched:
            return False

    for pod_annotation in sts_object["spec"]["template"]["metadata"][
        "annotations"
    ]:
        if pod_annotation.startswith("anvil.dev/"):
            # allow anvil annotations
            continue
        if (
            desired_annotations is None
            or pod_annotation not in desired_annotations
        ):
            # annotation is not in input, but in sts
            annotation_matched = False
            logging.info("annotation is not in input, but in sts")
            break
        if (
            sts_object["spec"]["template"]["metadata"]["annotations"][
                pod_annotation
            ]
            != desired_annotations[pod_annotation]
        ):
            # annotation value not match
            annotation_matched = False
            logging.info("annotation value not match")
            break

    return annotation_matched


def check_labels(
    desired_labels: dict, sts_object: k8s_models.V1StatefulSet
) -> bool:
    """Check if labels match"""
    label_matched = True
    if desired_labels is not None:
        # check if input labels are in sts
        for pod_label in desired_labels:
            if (
                pod_label
                not in sts_object["spec"]["template"]["metadata"]["labels"]
            ):
                # annotation is not in sts, but in input
                label_matched = False
                logging.info("label is not in sts, but in input")
                break
            if (
                sts_object["spec"]["template"]["metadata"]["labels"][pod_label]
                != desired_labels[pod_label]
            ):
                # annotation value not match
                label_matched = False
                logging.info("label value not match")
                break
        if not label_matched:
            return False

    for pod_label in sts_object["spec"]["template"]["metadata"]["labels"]:
        if pod_label == "app":
            # allow app label
            continue
        if desired_labels is None or pod_label not in desired_labels:
            # annotation is not in input, but in sts
            label_matched = False
            logging.info("label is not in input, but in sts")
            break
        if (
            sts_object["spec"]["template"]["metadata"]["labels"][pod_label]
            != desired_labels[pod_label]
        ):
            # annotation value not match
            label_matched = False
            logging.info("label value not match")
            break

    return label_matched


class MeasurementRunner(Runner):
    """Runner for performance measurement"""

    cr_config_to_zk_config = {
        "autoPurgePurgeInterval": "autopurge.purgeInterval",
        "autoPurgeSnapRetainCount": "autopurge.snapRetainCount",
        "commitLogCount": "commitLogCount",
        "globalOutstandingLimit": "globalOutstandingLimit",
        "initLimit": "initLimit",
        "maxClientCnxns": "maxClientCnxns",
        "maxSessionTimeout": "maxSessionTimeout",
        "minSessionTimeout": "minSessionTimeout",
        "preAllocSize": "preAllocSize",
        "quorumListenOnAllIPs": "quorumListenOnAllIPs",
        "snapCount": "snapCount",
        "snapSizeLimitInKb": "snapSizeLimitInKb",
        "syncLimit": "syncLimit",
        "tickTime": "tickTime",
    }

    def __init__(
        self,
        namespace: str,
        crd: dict,
        trial_dir: str,
        kubeconfig: str,
        context_name: str,
        wait_time: int = 45,
    ):
        self.namespace = namespace
        self.crd_metainfo: dict = crd
        self.trial_dir = trial_dir
        self.kubeconfig = kubeconfig
        self.context_name = context_name
        self.wait_time = wait_time
        self.log_length = 0

        self.kubectl_client = KubectlClient(kubeconfig, context_name)

        self.apiclient = kubernetes_client(kubeconfig, context_name)
        self.apiclient.configuration.verify_ssl = False
        self.coreV1Api = kubernetes.client.CoreV1Api(self.apiclient)
        self.appV1Api = kubernetes.client.AppsV1Api(self.apiclient)
        self.batchV1Api = kubernetes.client.BatchV1Api(self.apiclient)
        self.customObjectApi = kubernetes.client.CustomObjectsApi(
            self.apiclient
        )
        self.policyV1Api = kubernetes.client.PolicyV1Api(self.apiclient)
        self.networkingV1Api = kubernetes.client.NetworkingV1Api(self.apiclient)
        self.rbacAuthorizationV1Api = kubernetes.client.RbacAuthorizationV1Api(
            self.apiclient
        )
        self.storageV1Api = kubernetes.client.StorageV1Api(self.apiclient)
        self.schedulingV1Api = kubernetes.client.SchedulingV1Api(self.apiclient)
        self.resource_methods = {
            "pod": self.coreV1Api.list_namespaced_pod,
            "stateful_set": self.appV1Api.list_namespaced_stateful_set,
            "deployment": self.appV1Api.list_namespaced_deployment,
            "config_map": self.coreV1Api.list_namespaced_config_map,
            "service": self.coreV1Api.list_namespaced_service,
            "pvc": self.coreV1Api.list_namespaced_persistent_volume_claim,
            "cronjob": self.batchV1Api.list_namespaced_cron_job,
            "ingress": self.networkingV1Api.list_namespaced_ingress,
            "network_policy": self.networkingV1Api.list_namespaced_network_policy,
            "pod_disruption_budget": self.policyV1Api.list_namespaced_pod_disruption_budget,
            "secret": self.coreV1Api.list_namespaced_secret,
            "endpoints": self.coreV1Api.list_namespaced_endpoints,
            "service_account": self.coreV1Api.list_namespaced_service_account,
            "job": self.batchV1Api.list_namespaced_job,
            "role": self.rbacAuthorizationV1Api.list_namespaced_role,
            "role_binding": self.rbacAuthorizationV1Api.list_namespaced_role_binding,
        }

    def run(
        self,
        input: dict,
        sts_name_f: Callable[[dict], str],
        daemon_set_name_f: Callable[[dict], str],
        generation: int,
    ) -> MeasurementResult:
        """
        Run the input CRD and check if the condition is satisfied

        Args:
            input (dict): The input CR
            condition_1 (ConditionFuncType):
                A blocking function that checks if the condition is satisfied
            generation (int): The generation number of the input CR
        """
        logger = get_thread_logger(with_prefix=True)
        mutated_filename = "%s/mutated-%d.yaml" % (self.trial_dir, generation)
        with open(mutated_filename, "w") as mutated_cr_file:
            yaml.dump(input, mutated_cr_file)

        self.system_state_path = "%s/system-state-%03d.json" % (
            self.trial_dir,
            generation,
        )

        cmd = ["apply", "-f", mutated_filename, "-n", self.namespace]

        cli_result = self.kubectl_client.kubectl(
            cmd, capture_output=True, text=True
        )

        if cli_result.returncode != 0:
            logger.error(
                "kubectl apply failed with return code %d"
                % cli_result.returncode
            )
            logger.error("STDOUT: " + cli_result.stdout)
            logger.error("STDERR: " + cli_result.stderr)
            return None

        start_time = time.time()
        sts_name = sts_name_f(input) if sts_name_f else None
        daemon_set_name = (
            daemon_set_name_f(input) if daemon_set_name_f else None
        )
        event_list = MeasurementRunner.wait_for_converge(
            input=input,
            apiclient=self.apiclient,
            namespace=self.namespace,
            sts_name=sts_name,
            daemon_set_name=daemon_set_name,
        )

        acto_dumps = partial(json.dumps, cls=ActoEncoder)
        condition_1 = None
        condition_2 = None
        if sts_name_f:
            if len(event_list) == 1:
                condition_1 = event_list[-1][1]
                condition_2 = event_list[-1][1]
            else:
                last_revision = event_list[-1][0][
                    "object"
                ].status.update_revision
                last_spec = event_list[-1][0]["object"].to_dict()["spec"]
                # remove the lastRestartAt label for rabbitmq, hack for the reference rabbitmq operator
                # if "rabbitmq.com/lastRestartAt" in last_spec["template"]["metadata"]["labels"]:
                #     del last_spec["template"]["metadata"]["labels"]["rabbitmq.com/lastRestartAt"]
                last_spec_hash = hashlib.sha256(
                    json.dumps(last_spec, sort_keys=True).encode()
                ).hexdigest()

                prev_spec = None
                for event, timestamp in event_list:
                    obj_dict = event["object"].to_dict()
                    dt_object = datetime.fromtimestamp(timestamp)
                    logger.info(
                        f"{event['type']} {event['object'].metadata.name} at {timestamp} - {dt_object}"
                    )
                    patch = jsonpatch.JsonPatch.from_diff(
                        prev_spec, obj_dict["spec"], dumps=acto_dumps
                    )
                    logger.info(f"Patch: {patch.to_string(dumps=acto_dumps)}")

                    curr_spec = obj_dict["spec"]
                    # remove the lastRestartAt label for rabbitmq, hack for the reference rabbitmq operator
                    # if "rabbitmq.com/lastRestartAt" in curr_spec["template"]["metadata"]["annotations"]:
                    #     del curr_spec["template"]["metadata"]["labels"]["rabbitmq.com/lastRestartAt"]
                    current_spec_hash = hashlib.sha256(
                        json.dumps(curr_spec, sort_keys=True).encode()
                    ).hexdigest()
                    prev_spec = curr_spec
                    if condition_1 is None:
                        if current_spec_hash == last_spec_hash:
                            condition_1 = timestamp
                        else:
                            continue

                    if condition_2 is None:
                        if (
                            event["object"].status.ready_replicas
                            == event["object"].spec.replicas
                            and event["object"].status.current_revision
                            == last_revision
                        ):
                            condition_2 = timestamp
                            break
                        else:
                            continue
                # last_revision = event_list[-1][0]["object"].status.update_revision
                # for sts_event, timestamp in event_list:
                #     dt_object = datetime.fromtimestamp(timestamp)
                #     logger.info(
                #         f"{sts_event['type']} {sts_event['object'].metadata.name} at {timestamp} - {dt_object}")

                #     if condition_1 is None:
                #         if sts_event["object"].status.update_revision == last_revision:
                #             condition_1 = timestamp
                #         else:
                #             continue

                #     if condition_2 is None:
                #         if (sts_event["object"].status.ready_replicas == input["spec"]["replicas"]
                #                 and sts_event["object"].status.current_revision == last_revision):
                #             condition_2 = timestamp
                #             break
                #         else:
                #             continue
        elif daemon_set_name_f:
            if len(event_list) == 1:
                condition_1 = event_list[-1][1]
                condition_2 = event_list[-1][1]
            else:
                last_spec = event_list[-1][0]["object"].to_dict()["spec"]
                last_spec_hash = hashlib.sha256(
                    json.dumps(last_spec, sort_keys=True).encode()
                ).hexdigest()
                prev_obj = None

                for ds_event, timestamp in event_list:
                    obj_dict = ds_event["object"].to_dict()
                    dt_object = datetime.fromtimestamp(timestamp)
                    logger.info(
                        f"{ds_event['type']} {obj_dict['metadata']['name']} at {timestamp} - {dt_object}"
                    )
                    patch = jsonpatch.JsonPatch.from_diff(
                        prev_obj, obj_dict, dumps=acto_dumps
                    )
                    logger.info(f"Patch: {patch.to_string(dumps=acto_dumps)}")

                    prev_obj = obj_dict
                    current_spec_hash = hashlib.sha256(
                        json.dumps(obj_dict["spec"], sort_keys=True).encode()
                    ).hexdigest()
                    if condition_1 is None:
                        if current_spec_hash == last_spec_hash:
                            condition_1 = timestamp
                        else:
                            continue

                    if condition_2 is None:
                        if (
                            ds_event["object"].status.number_ready
                            != ds_event[
                                "object"
                            ].status.desired_number_scheduled
                        ):
                            logging.info(
                                "number_ready != desired_number_scheduled"
                            )
                        elif (
                            ds_event["object"].status.observed_generation
                            != ds_event["object"].metadata.generation
                        ):
                            logging.info(
                                "observed_generation != metadata.generation"
                            )
                        elif current_spec_hash != last_spec_hash:
                            logging.info("current_spec_hash != last_spec_hash")
                        else:
                            condition_2 = timestamp
                            break
        else:
            raise ValueError(
                "Either sts_name_f or daemon_set_name_f must be provided"
            )

        # condition_1(input, self.apiclient, self.namespace)
        # timestamp_1 = time.time()
        # condition_2(input, self.apiclient, self.namespace)
        # timestamp_2 = time.time()

        duration_1 = condition_1 - start_time
        logging.info("Condition 1 took %f seconds" % duration_1)

        duration_2 = condition_2 - start_time
        logging.info("Condition 2 took %f seconds" % duration_2)

        with open(
            "%s/sts-events-%03d.json" % (self.trial_dir, generation), "w"
        ) as system_state_file:
            json.dump(
                [
                    {"ts": ts, "statefulset": sts["object"].to_dict()}
                    for sts, ts in event_list
                ],
                system_state_file,
                cls=ActoEncoder,
                indent=4,
            )

        self.collect_system_state()

        return MeasurementResult(start_time, condition_1, condition_2)

    @staticmethod
    def wait_for_reference_zk_spec(
        input: dict, apiclient: kubernetes.client.ApiClient, namespace: str
    ) -> bool:
        appV1Api = kubernetes.client.AppsV1Api(apiclient)
        coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        watch = kubernetes.watch.Watch()

        configmap_name = f"{input['metadata']['name']}-configmap"
        for event in watch.stream(
            func=coreV1Api.list_namespaced_config_map,
            namespace=namespace,
            field_selector=f"metadata.name={configmap_name}",
        ):
            obj: k8s_models.V1ConfigMap = event["object"]
            logging.info("Checking configmap")

            zk_config_str = obj.data["zoo.cfg"]
            logging.info(zk_config_str)
            config_dict = {}
            for line in zk_config_str.split("\n"):
                name, var = line.partition("=")[::2]
                config_dict[name.strip()] = var.strip()

            config_matched = True
            for cr_config in MeasurementRunner.cr_config_to_zk_config:
                if cr_config in input["spec"]["config"]:
                    if (
                        str(input["spec"]["config"][cr_config]).lower()
                        != str(
                            config_dict[
                                MeasurementRunner.cr_config_to_zk_config[
                                    cr_config
                                ]
                            ]
                        ).lower()
                    ):
                        config_matched = False
                        logging.info(
                            f"config {cr_config} not matched, expected {input['spec']['conf'][cr_config]}, actual {config_dict[MeasurementRunner.cr_config_to_zk_config[cr_config]]}"
                        )
                        break
            if not config_matched:
                logging.info("config not matched")
                continue

            break

        logging.info("Configmap matched, Checking sts")

        sts_name = input["metadata"]["name"]
        for event in watch.stream(
            func=appV1Api.list_namespaced_stateful_set,
            namespace=namespace,
            field_selector="metadata.name=%s" % sts_name,
        ):
            sts_object = event["object"].to_dict()
            logging.info(json.dumps(sts_object, indent=4, cls=ActoEncoder))

            if "pod" in input["spec"] and "affinity" in input["spec"]["pod"]:
                desired_affinity = input["spec"]["pod"]["affinity"]
                if not check_affinity(desired_affinity, sts_object):
                    continue

            if sts_object["spec"]["replicas"] != input["spec"]["replicas"]:
                continue

            expected_image = (
                input["spec"]["image"]["repository"]
                + ":"
                + input["spec"]["image"]["tag"]
            )
            if (
                sts_object["spec"]["template"]["spec"]["containers"][0]["image"]
                != expected_image
            ):
                logging.info("image not matched")
                continue

            port_matched = True
            input_port_map = {}
            for port in input["spec"]["ports"]:
                input_port_map[port["name"]] = port["containerPort"]

            for port in sts_object["spec"]["template"]["spec"]["containers"][0][
                "ports"
            ]:
                if (
                    port["name"] == "admin-server"
                    and port["container_port"] != input_port_map["admin-server"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "client"
                    and port["container_port"] != input_port_map["client"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "leader-election"
                    and port["container_port"]
                    != input_port_map["leader-election"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "metrics"
                    and port["container_port"] != input_port_map["metrics"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "quorum"
                    and port["container_port"] != input_port_map["quorum"]
                ):
                    port_matched = False
            if not port_matched:
                logging.info("port not matched")
                continue

            if (
                "pod" in input["spec"]
                and "resources" in input["spec"]["pod"]
                and input["spec"]["pod"]["resources"]
            ):
                resource_matched = True
                if (
                    "limits" in input["spec"]["pod"]["resources"]
                    and input["spec"]["pod"]["resources"]["limits"]
                ):
                    if (
                        "limits"
                        not in sts_object["spec"]["template"]["spec"][
                            "containers"
                        ][0]["resources"]
                        or not sts_object["spec"]["template"]["spec"][
                            "containers"
                        ][0]["resources"]["limits"]
                    ):
                        resource_matched = False
                    else:
                        for resource in input["spec"]["pod"]["resources"][
                            "limits"
                        ]:
                            if (
                                input["spec"]["pod"]["resources"]["limits"][
                                    resource
                                ]
                                != sts_object["spec"]["template"]["spec"][
                                    "containers"
                                ][0]["resources"]["limits"][resource]
                            ):
                                resource_matched = False
                else:
                    if (
                        "limits"
                        in sts_object["spec"]["template"]["spec"]["containers"][
                            0
                        ]["resources"]
                        and sts_object["spec"]["template"]["spec"][
                            "containers"
                        ][0]["resources"]["limits"]
                    ):
                        resource_matched = False

                if (
                    "requests" in input["spec"]["pod"]["resources"]
                    and input["spec"]["pod"]["resources"]["requests"]
                ):
                    if (
                        "requests"
                        not in sts_object["spec"]["template"]["spec"][
                            "containers"
                        ][0]["resources"]
                        or not sts_object["spec"]["template"]["spec"][
                            "containers"
                        ][0]["resources"]["requests"]
                    ):
                        resource_matched = False
                    else:
                        for resource in input["spec"]["pod"]["resources"][
                            "requests"
                        ]:
                            if (
                                input["spec"]["pod"]["resources"]["requests"][
                                    resource
                                ]
                                != sts_object["spec"]["template"]["spec"][
                                    "containers"
                                ][0]["resources"]["requests"][resource]
                            ):
                                resource_matched = False
                else:
                    if (
                        "requests"
                        in sts_object["spec"]["template"]["spec"]["containers"][
                            0
                        ]["resources"]
                        and sts_object["spec"]["template"]["spec"][
                            "containers"
                        ][0]["resources"]["requests"]
                    ):
                        resource_matched = False
                if not resource_matched:
                    logging.info("resource not matched")
                    continue

            desired_toleration = (
                input["spec"]["pod"]["tolerations"]
                if "pod" in input["spec"]
                and "tolerations" in input["spec"]["pod"]
                else None
            )
            if not check_tolerations(desired_toleration, sts_object):
                logging.info("toleration not matched")
                continue

            # check if annotations match
            input_annotations = (
                input["spec"]["annotations"]
                if "pod" in input["spec"]
                and "annotations" in input["spec"]["pod"]
                else None
            )
            if not check_annotations(input_annotations, sts_object):
                logging.info("annotation not matched")
                continue

            # check if labels match
            input_labels = (
                input["spec"]["labels"]
                if "pod" in input["spec"] and "labels" in input["spec"]["pod"]
                else None
            )
            if not check_labels(input_labels, sts_object):
                logging.info("label not matched")
                continue

            if (
                sts_object["metadata"]["generation"]
                != sts_object["status"]["observed_generation"]
            ):
                logging.info("generation not matched")
                continue

            break

    @staticmethod
    def wait_for_zk_spec(
        input: dict, apiclient: kubernetes.client.ApiClient, namespace: str
    ) -> bool:
        appV1Api = kubernetes.client.AppsV1Api(apiclient)
        coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        watch = kubernetes.watch.Watch()

        configmap_name = f"{input['metadata']['name']}-configmap"
        for event in watch.stream(
            func=coreV1Api.list_namespaced_config_map,
            namespace=namespace,
            field_selector=f"metadata.name={configmap_name}",
        ):
            obj: k8s_models.V1ConfigMap = event["object"]

            zk_config_str = obj.data["zoo.cfg"]
            logging.info(zk_config_str)
            config_dict = {}
            for line in zk_config_str.split("\n"):
                name, var = line.partition("=")[::2]
                config_dict[name.strip()] = var.strip()

            logging.info(json.dumps(config_dict, indent=4, cls=ActoEncoder))

            config_matched = True
            for cr_config in MeasurementRunner.cr_config_to_zk_config:
                if cr_config in input["spec"]["conf"]:
                    if (
                        str(input["spec"]["conf"][cr_config]).lower()
                        != str(
                            config_dict[
                                MeasurementRunner.cr_config_to_zk_config[
                                    cr_config
                                ]
                            ]
                        ).lower()
                    ):
                        config_matched = False
                        logging.info(
                            f"config {cr_config} not matched, expected {input['spec']['conf'][cr_config]}, actual {config_dict[MeasurementRunner.cr_config_to_zk_config[cr_config]]}"
                        )
                        break
            if not config_matched:
                continue

            break

        sts_name = input["metadata"]["name"]
        for event in watch.stream(
            func=appV1Api.list_namespaced_stateful_set,
            namespace=namespace,
            field_selector="metadata.name=%s" % sts_name,
        ):
            sts_object = event["object"].to_dict()
            logging.info(json.dumps(sts_object, indent=4, cls=ActoEncoder))

            if "affinity" in input["spec"]:
                desired_affinity = input["spec"]["affinity"]
                if not check_affinity(desired_affinity, sts_object):
                    logging.info("affinity not matched")
                    continue

            # check if replicas match
            if sts_object["spec"]["replicas"] != input["spec"]["replicas"]:
                continue

            # check if image matches
            if (
                sts_object["spec"]["template"]["spec"]["containers"][0]["image"]
                != input["spec"]["image"]
            ):
                continue

            # check if ports match
            port_matched = True
            for port in sts_object["spec"]["template"]["spec"]["containers"][0][
                "ports"
            ]:
                if (
                    port["name"] == "adminServer"
                    and port["container_port"]
                    != input["spec"]["ports"]["adminPort"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "client"
                    and port["container_port"]
                    != input["spec"]["ports"]["client"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "leaderElection"
                    and port["container_port"]
                    != input["spec"]["ports"]["leaderElection"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "metrics"
                    and port["container_port"]
                    != input["spec"]["ports"]["metrics"]
                ):
                    port_matched = False
                elif (
                    port["name"] == "quorum"
                    and port["container_port"]
                    != input["spec"]["ports"]["quorum"]
                ):
                    port_matched = False
            if not port_matched:
                logging.info("port not matched")
                continue

            # check if resources match
            desired_resources = (
                input["spec"]["resources"]
                if "resources" in input["spec"]
                else None
            )
            if not check_resources(desired_resources, sts_object):
                logging.info("resource not matched")
                continue

            # check if annotations match
            input_annotations = (
                input["spec"]["annotations"]
                if "annotations" in input["spec"]
                else None
            )
            if not check_annotations(input_annotations, sts_object):
                logging.info("annotation not matched")
                continue

            # check if labels match
            input_labels = (
                input["spec"]["labels"] if "labels" in input["spec"] else None
            )
            if not check_labels(input_labels, sts_object):
                logging.info("label not matched")
                continue

            desired_toleration = (
                input["spec"]["tolerations"]
                if "tolerations" in input["spec"]
                else None
            )
            if not check_tolerations(desired_toleration, sts_object):
                logging.info("toleration not matched")
                continue

            # make sure the generation is up to date
            if (
                sts_object["metadata"]["generation"]
                != sts_object["status"]["observed_generation"]
            ):
                logging.info("generation not matched")
                continue

            configmap: k8s_models.V1ConfigMap = (
                coreV1Api.read_namespaced_config_map(configmap_name, namespace)
            )
            if (
                sts_object["spec"]["template"]["metadata"]["annotations"][
                    "anvil.dev/lastRestartAt"
                ]
                != configmap.metadata.resource_version
            ):
                continue

            break

        return True

    @staticmethod
    def wait_for_reference_rabbitmq_spec(
        input: dict, apiclient: kubernetes.client.ApiClient, namespace: str
    ) -> bool:
        appV1Api = kubernetes.client.AppsV1Api(apiclient)
        coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        watch = kubernetes.watch.Watch()

        sts_name = f"{input['metadata']['name']}-server"
        for event in watch.stream(
            func=appV1Api.list_namespaced_stateful_set,
            namespace=namespace,
            field_selector="metadata.name=%s" % sts_name,
        ):
            sts_object = event["object"].to_dict()
            logging.info(json.dumps(sts_object, indent=4, cls=ActoEncoder))

            # affinity
            desired_affinity = (
                input["spec"]["affinity"]
                if "affinity" in input["spec"]
                else None
            )
            if not check_affinity(desired_affinity, sts_object):
                continue

            desired_annotations = None
            desired_labels = None
            desired_persistent_volume_claim_retention_policy = None
            desired_pod_management_policy = None
            if "override" in input["spec"]:
                if "statefulSet" in input["spec"]["override"]:
                    if "spec" in input["spec"]["override"]["statefulSet"]:
                        if (
                            "template"
                            in input["spec"]["override"]["statefulSet"]["spec"]
                        ):
                            if (
                                "metadata"
                                in input["spec"]["override"]["statefulSet"][
                                    "spec"
                                ]["template"]
                            ):
                                if (
                                    "annotations"
                                    in input["spec"]["override"]["statefulSet"][
                                        "spec"
                                    ]["template"]["metadata"]
                                ):
                                    desired_annotations = input["spec"][
                                        "override"
                                    ]["statefulSet"]["spec"]["template"][
                                        "metadata"
                                    ][
                                        "annotations"
                                    ]
                                if (
                                    "labels"
                                    in input["spec"]["override"]["statefulSet"][
                                        "spec"
                                    ]["template"]["metadata"]
                                ):
                                    desired_labels = input["spec"]["override"][
                                        "statefulSet"
                                    ]["spec"]["template"]["metadata"]["labels"]

                        if (
                            "persistentVolumeClaimRetentionPolicy"
                            in input["spec"]["override"]["statefulSet"]["spec"]
                        ):
                            desired_persistent_volume_claim_retention_policy = (
                                input["spec"]["override"]["statefulSet"][
                                    "spec"
                                ]["persistentVolumeClaimRetentionPolicy"]
                            )

                        if (
                            "podManagementPolicy"
                            in input["spec"]["override"]["statefulSet"]["spec"]
                        ):
                            desired_pod_management_policy = input["spec"][
                                "override"
                            ]["statefulSet"]["spec"]["podManagementPolicy"]
            # annotations
            if not check_annotations(desired_annotations, sts_object):
                logging.info("annotation not matched")
                continue

            # image
            if (
                sts_object["spec"]["template"]["spec"]["containers"][0]["image"]
                != input["spec"]["image"]
            ):
                logging.info("image not matched")
                continue

            # labels
            if not check_labels(desired_labels, sts_object):
                logging.info("label not matched")
                continue

            # persistence
            if "persistence" in input["spec"]:
                pvc_template = sts_object["spec"]["volume_claim_templates"][0]
                if "storage" in input["spec"]["persistence"]:
                    if (
                        pvc_template["spec"]["resources"]["requests"]["storage"]
                        != input["spec"]["persistence"]["storage"]
                    ):
                        continue

                if "storageClassName" in input["spec"]["persistence"]:
                    if (
                        pvc_template["spec"]["storage_class_name"]
                        != input["spec"]["persistence"]["storageClassName"]
                    ):
                        continue

            # persistentVolumeClaimRetentionPolicy
            if not check_persistent_volume_claim_retention_policy(
                desired_persistent_volume_claim_retention_policy, sts_object
            ):
                logging.info("persistentVolumeClaimRetentionPolicy not matched")
                continue

            # podManagementPolicy
            if (
                desired_pod_management_policy != None
                and sts_object["spec"]["pod_management_policy"]
                != desired_pod_management_policy
            ):
                logging.info("podManagementPolicy not matched")
                continue

            # replicas
            if sts_object["spec"]["replicas"] != input["spec"]["replicas"]:
                continue

            # resources
            desired_resources = (
                input["spec"]["resources"]
                if "resources" in input["spec"]
                else None
            )
            if not check_resources(desired_resources, sts_object):
                continue

            # tolerations
            desired_tolerations = (
                input["spec"]["tolerations"]
                if "tolerations" in input["spec"]
                else None
            )
            if not check_tolerations(desired_tolerations, sts_object):
                continue

            # make sure the generation is up to date
            if (
                sts_object["metadata"]["generation"]
                != sts_object["status"]["observed_generation"]
            ):
                logging.info("generation not matched")
                continue

            break

    @staticmethod
    def wait_for_rabbitmq_spec(
        input: dict, apiclient: kubernetes.client.ApiClient, namespace: str
    ) -> bool:
        appV1Api = kubernetes.client.AppsV1Api(apiclient)
        coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        watch = kubernetes.watch.Watch()

        sts_name = f"{input['metadata']['name']}-server"
        for event in watch.stream(
            func=appV1Api.list_namespaced_stateful_set,
            namespace=namespace,
            field_selector="metadata.name=%s" % sts_name,
        ):
            sts_object = event["object"].to_dict()
            logging.info(json.dumps(sts_object, indent=4, cls=ActoEncoder))

            # affinity
            desired_affinity = (
                input["spec"]["affinity"]
                if "affinity" in input["spec"]
                else None
            )
            if not check_affinity(desired_affinity, sts_object):
                logging.info("affinity not matched")
                continue

            # annotations
            input_annotations = (
                input["spec"]["annotations"]
                if "annotations" in input["spec"]
                else None
            )
            if not check_annotations(input_annotations, sts_object):
                logging.info("annotation not matched")
                continue

            # image
            if (
                sts_object["spec"]["template"]["spec"]["containers"][0]["image"]
                != input["spec"]["image"]
            ):
                logging.info("image not matched")
                continue

            # labels
            input_labels = (
                input["spec"]["labels"] if "labels" in input["spec"] else None
            )
            if not check_labels(input_labels, sts_object):
                logging.info("label not matched")
                continue

            # persistence
            if "persistence" in input["spec"]:
                pvc_template = sts_object["spec"]["volume_claim_templates"][0]
                if (
                    "storage" in input["spec"]["persistence"]
                    and input["spec"]["persistence"]["storage"] is not None
                ):
                    if (
                        pvc_template["spec"]["resources"]["requests"]["storage"]
                        != input["spec"]["persistence"]["storage"]
                    ):
                        logging.info("storage not matched")
                        continue

                if (
                    "storageClassName" in input["spec"]["persistence"]
                    and input["spec"]["persistence"]["storageClassName"]
                    is not None
                ):
                    if (
                        pvc_template["spec"]["storage_class_name"]
                        != input["spec"]["persistence"]["storageClassName"]
                    ):
                        logging.info("storageClassName not matched")
                        continue

            # persistentVolumeClaimRetentionPolicy
            desired_persistent_volume_claim_retention_policy = (
                input["spec"]["persistentVolumeClaimRetentionPolicy"]
                if "persistentVolumeClaimRetentionPolicy" in input["spec"]
                else None
            )
            if not check_persistent_volume_claim_retention_policy(
                desired_persistent_volume_claim_retention_policy, sts_object
            ):
                logging.info("persistentVolumeClaimRetentionPolicy not matched")
                continue

            # podManagementPolicy
            if "podManagementPolicy" in input["spec"]:
                if (
                    sts_object["spec"]["pod_management_policy"]
                    != input["spec"]["podManagementPolicy"]
                ):
                    logging.info("podManagementPolicy not matched")
                    continue

            # rabbitmqConfig

            # replicas
            if sts_object["spec"]["replicas"] != input["spec"]["replicas"]:
                logging.info("replicas not matched")
                continue

            # resources
            desired_resources = (
                input["spec"]["resources"]
                if "resources" in input["spec"]
                else None
            )
            if not check_resources(desired_resources, sts_object):
                logging.info("resources not matched")
                continue

            # tolerations
            desired_tolerations = (
                input["spec"]["tolerations"]
                if "tolerations" in input["spec"]
                else None
            )
            if not check_tolerations(desired_tolerations, sts_object):
                logging.info("tolerations not matched")
                continue

            # make sure the generation is up to date
            if (
                sts_object["metadata"]["generation"]
                != sts_object["status"]["observed_generation"]
            ):
                logging.info("generation not matched")
                continue

            break

    @staticmethod
    def wait_for_pod_ready(
        input: dict, apiclient: kubernetes.client.ApiClient, namespace: str
    ) -> bool:
        coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        appV1Api = kubernetes.client.AppsV1Api(apiclient)
        watch = kubernetes.watch.Watch()

        for event in watch.stream(
            func=appV1Api.list_namespaced_stateful_set, namespace=namespace
        ):
            sts_object = event["object"].to_dict()

            if (
                sts_object["status"]["current_revision"]
                != sts_object["status"]["update_revision"]
            ):
                continue

            if (
                sts_object["status"]["ready_replicas"]
                != input["spec"]["replicas"]
            ):
                continue

            break

        for event in watch.stream(
            func=coreV1Api.list_namespaced_pod, namespace=namespace
        ):
            pod_object = event["object"].to_dict()
            logging.info(json.dumps(pod_object, indent=4, cls=ActoEncoder))

            if pod_object["status"]["phase"] != "Running":
                continue

            containers_ready = True
            for container_status in pod_object["status"]["container_statuses"]:
                if container_status["ready"] != True:
                    containers_ready = False
                    break
            if not containers_ready:
                continue

            break

        return True

    @staticmethod
    def wait_for_converge(
        input: dict,
        apiclient: kubernetes.client.ApiClient,
        namespace: str,
        sts_name: str = None,
        daemon_set_name: str = None,
    ) -> list:
        appV1Api = kubernetes.client.AppsV1Api(apiclient)
        watch = kubernetes.watch.Watch()

        statefulset_updates = []
        statefulset_updates_queue = Queue(maxsize=0)

        if sts_name is not None:
            stream = watch.stream(
                func=appV1Api.list_namespaced_stateful_set,
                namespace=namespace,
                field_selector="metadata.name=%s" % sts_name,
            )
        elif daemon_set_name is not None:
            stream = watch.stream(
                func=appV1Api.list_namespaced_daemon_set,
                namespace=namespace,
                field_selector="metadata.name=%s" % daemon_set_name,
            )

        timer_hard_timeout = acto_timer.ActoTimer(
            900, statefulset_updates_queue, "timeout"
        )
        watch_process = Process(
            target=MeasurementRunner.watch_system_events,
            args=(stream, statefulset_updates_queue),
        )

        timer_hard_timeout.start()
        watch_process.start()

        while True:
            try:
                statefulset_event = statefulset_updates_queue.get(timeout=120)
                if (
                    isinstance(statefulset_event, str)
                    and statefulset_event == "timeout"
                ):
                    break
                else:
                    statefulset_updates.append(statefulset_event)
            except queue.Empty:
                if check_pods_ready(input, apiclient, namespace):
                    break
                else:
                    logging.info("pods not ready")
                    continue

        stream.close()
        timer_hard_timeout.cancel()
        watch_process.terminate()

        return statefulset_updates

    @staticmethod
    def watch_system_events(event_stream, queue: Queue):
        """A process that watches namespaced events"""
        for object in event_stream:
            try:
                logging.info(f"event type: {object['type']}")
                ts = time.time()
                queue.put((object, ts))
            except (ValueError, AssertionError):
                pass

    @staticmethod
    def zk_sts_name(input: dict):
        return input["metadata"]["name"]

    @staticmethod
    def rabbitmq_sts_name(input: dict):
        return f"{input['metadata']['name']}-server"

    @staticmethod
    def fluent_ds_name(input: dict):
        return f"{input['metadata']['name']}"
