"""Runner for performance measurement"""

import copy
import hashlib
import json
import logging
import queue
import time
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from multiprocessing import Process, Queue
from typing import Callable, Optional

import deepdiff
import jsonpatch
import kubernetes
import kubernetes.client.models as k8s_models
import yaml
from urllib3.exceptions import SSLError

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
    condition_3_ts: Optional[float] = None


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
        context = {"namespace": namespace, "crd": crd}
        super().__init__(
            context, trial_dir, kubeconfig, context_name, wait_time=wait_time
        )
        self.apiclient.configuration.verify_ssl = False

    def measure(
        self,
        input: dict,
        sts_name_f: Optional[Callable[[dict], str]],
        daemon_set_name_f: Optional[Callable[[dict], str]],
        generation: int,
        vdeployment_name_f: Optional[Callable[[dict], str]] = None,
        deployment_name_f: Optional[Callable[[dict], str]] = None,
    ) -> Optional[MeasurementResult]:
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

        condition_3 = None
        if vdeployment_name_f:
            condition_1, condition_2, condition_3 = self._measure_vdeployment(
                input, generation, vdeployment_name_f(input)
            )
        elif deployment_name_f:
            condition_1, condition_2, condition_3 = self._measure_deployment(
                input, generation, deployment_name_f(input)
            )
        else:
            condition_1, condition_2 = self._measure_sts_or_ds(
                input,
                generation,
                sts_name_f,
                daemon_set_name_f,
            )

        duration_1 = condition_1 - start_time
        logging.info("Condition 1 took %f seconds" % duration_1)

        duration_2 = condition_2 - start_time
        logging.info("Condition 2 took %f seconds" % duration_2)

        if condition_3 is not None:
            duration_3 = condition_3 - start_time
            logging.info("Condition 3 took %f seconds" % duration_3)

        if self.crd_metainfo:
            self.collect_system_state()

        return MeasurementResult(start_time, condition_1, condition_2, condition_3)

    def _measure_vdeployment(
        self, input: dict, generation: int, vdeployment_name: str
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        logger = get_thread_logger(with_prefix=True)
        custom_api = kubernetes.client.CustomObjectsApi(self.apiclient)

        event_list = MeasurementRunner.wait_for_vdeployment_converge(
            input=input,
            apiclient=self.apiclient,
            namespace=self.namespace,
            vdeployment_name=vdeployment_name,
        )

        desired_template = input["spec"].get("template", {})
        desired_replicas = input["spec"].get("replicas", 1)
        condition_1 = None
        condition_2 = None
        condition_3 = None
        for tag, event, timestamp in event_list:
            if tag == "vrs":
                logger.info(
                    f"{event['type']} VReplicaSet at {timestamp} - "
                    f"{datetime.fromtimestamp(timestamp)}"
                )
                # condition_1 is the latest timestamp any VRS was touched,
                # regardless of event type or which VRS it was.
                condition_1 = timestamp
            elif tag == "pod":
                event_type = event["type"]
                if event_type == "MODIFIED":
                    # condition_2 is the latest timestamp any pod was updated
                    condition_2 = timestamp
                elif event_type in ("ADDED", "DELETED"):
                    # condition_3 is the latest timestamp any pod was created or deleted
                    condition_3 = timestamp

        # Race condition fallback: the matching VRS may have been created before
        # the watch started.  Find it by comparing the pod template directly and
        # use its creationTimestamp as condition_1.
        matching_vrs = None
        if condition_1 is None or condition_2 is None or condition_3 is None:
            vrs_list = custom_api.list_namespaced_custom_object(
                group="anvil.dev",
                version="v1",
                namespace=self.namespace,
                plural="vreplicasets",
            )
            for vrs in vrs_list.get("items", []):
                vrs_template = copy.deepcopy(
                    vrs.get("spec", {}).get("template", {})
                )
                vrs_template.get("metadata", {}).get("labels", {}).pop(
                    "pod-template-hash", None
                )
                if not deepdiff.DeepDiff(
                    desired_template, vrs_template, ignore_order=True
                ):
                    matching_vrs = vrs
                    break

        if condition_1 is None and matching_vrs is not None:
            creation_ts = matching_vrs.get("metadata", {}).get(
                "creationTimestamp"
            )
            if creation_ts is not None:
                condition_1 = datetime.fromisoformat(creation_ts).timestamp()
                logger.info(
                    f"condition_1 set via direct VRS lookup (created before "
                    f"watch started): {condition_1}"
                )

        # Condition_2 fallback: use pod Ready lastTransitionTime for the VRS's
        # own pods (identified via its selector labels).
        # Condition_3 fallback: use pod creationTimestamp.
        if (condition_2 is None or condition_3 is None) and matching_vrs is not None:
            match_labels = (
                matching_vrs.get("spec", {})
                .get("selector", {})
                .get("matchLabels", {})
            )
            label_selector = ",".join(
                f"{k}={v}" for k, v in match_labels.items()
            )
            core_v1 = kubernetes.client.CoreV1Api(self.apiclient)
            pods = core_v1.list_namespaced_pod(
                self.namespace, label_selector=label_selector
            )
            ready_times = []
            creation_times = []
            for pod in pods.items:
                if pod.metadata.creation_timestamp is not None:
                    creation_times.append(
                        pod.metadata.creation_timestamp.timestamp()
                    )
                for cond in pod.status.conditions or []:
                    if cond.type == "Ready" and cond.status == "True":
                        ready_times.append(
                            cond.last_transition_time.timestamp()
                        )
                        break
            if condition_2 is None:
                if len(ready_times) == 0 and desired_replicas == 0:
                    condition_2 = condition_1
                elif len(ready_times) >= desired_replicas:
                    condition_2 = max(ready_times)
                    logger.info(
                        f"condition_2 set via pod Ready lastTransitionTime "
                        f"fallback: {condition_2}"
                    )
            if condition_3 is None and creation_times:
                condition_3 = max(creation_times)
                logger.info(
                    f"condition_3 set via pod creationTimestamp fallback: "
                    f"{condition_3}"
                )

        with open(
            "%s/vrs-events-%03d.json" % (self.trial_dir, generation), "w"
        ) as f:
            json.dump(
                [
                    {"ts": ts, "vrs": event["object"]}
                    for tag, event, ts in event_list
                    if tag == "vrs"
                ],
                f,
                cls=ActoEncoder,
                indent=4,
            )
        return condition_1, condition_2, condition_3

    def _measure_deployment(
        self, input: dict, generation: int, deployment_name: str
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        logger = get_thread_logger(with_prefix=True)

        event_list = MeasurementRunner.wait_for_deployment_converge(
            input=input,
            apiclient=self.apiclient,
            namespace=self.namespace,
            deployment_name=deployment_name,
        )

        apps_v1 = kubernetes.client.AppsV1Api(self.apiclient)
        deployment = apps_v1.read_namespaced_deployment(
            name=deployment_name, namespace=self.namespace
        )
        deployment_revision = (deployment.metadata.annotations or {}).get(
            "deployment.kubernetes.io/revision"
        )

        desired_replicas = input["spec"].get("replicas", 1)
        condition_1 = None
        condition_2 = None
        condition_3 = None
        rs_prev_specs: dict[str, dict] = {}
        for tag, event, timestamp in event_list:
            if tag == "rs":
                rs_obj = event["object"]
                rs_name = rs_obj.metadata.name
                event_type = event["type"]
                logger.info(
                    f"{event_type} ReplicaSet {rs_name} at {timestamp} - "
                    f"{datetime.fromtimestamp(timestamp)}"
                )
                if event_type == "ADDED":
                    # New RS created — spec is being set for the first time
                    condition_1 = timestamp
                    rs_prev_specs[rs_name] = rs_obj.to_dict().get("spec", {})
                elif event_type == "MODIFIED":
                    current_spec = rs_obj.to_dict().get("spec", {})
                    prev_spec = rs_prev_specs.get(rs_name)
                    if prev_spec != current_spec:
                        condition_1 = timestamp
                    rs_prev_specs[rs_name] = current_spec
                elif event_type == "DELETED":
                    rs_prev_specs.pop(rs_name, None)
            elif tag == "pod":
                event_type = event["type"]
                if event_type == "MODIFIED":
                    # condition_2 is the latest timestamp any pod was updated
                    condition_2 = timestamp
                elif event_type in ("ADDED", "DELETED"):
                    # condition_3 is the latest timestamp any pod was created or deleted
                    condition_3 = timestamp

        # Race condition fallback: the RS may have been created before the
        # watch started.  Look it up directly and use its creationTimestamp.
        current_rs = None
        if (
            condition_1 is None or condition_2 is None or condition_3 is None
        ) and deployment_revision is not None:
            rs_list = apps_v1.list_namespaced_replica_set(self.namespace)
            for rs in rs_list.items:
                rs_revision = (rs.metadata.annotations or {}).get(
                    "deployment.kubernetes.io/revision"
                )
                is_owned = any(
                    ref.kind == "Deployment" and ref.name == deployment_name
                    for ref in (rs.metadata.owner_references or [])
                )
                if rs_revision == deployment_revision and is_owned:
                    current_rs = rs
                    break

        if condition_1 is None and current_rs is not None:
            creation_ts = current_rs.metadata.creation_timestamp
            if creation_ts is not None:
                condition_1 = creation_ts.timestamp()
                logger.info(
                    f"ReplicaSet with revision {deployment_revision} "
                    f"found via direct lookup (created before watch "
                    f"started), condition_1={condition_1}"
                )

        # Condition_2 fallback: use pod Ready lastTransitionTime.
        # Condition_3 fallback: use pod creationTimestamp.
        if (condition_2 is None or condition_3 is None) and current_rs is not None:
            rs_hash = (current_rs.metadata.labels or {}).get(
                "pod-template-hash"
            )
            core_v1 = kubernetes.client.CoreV1Api(self.apiclient)
            pods = core_v1.list_namespaced_pod(
                self.namespace,
                label_selector=f"pod-template-hash={rs_hash}",
            )
            ready_times = []
            creation_times = []
            for pod in pods.items:
                if pod.metadata.creation_timestamp is not None:
                    creation_times.append(
                        pod.metadata.creation_timestamp.timestamp()
                    )
                for cond in pod.status.conditions or []:
                    if cond.type == "Ready" and cond.status == "True":
                        ready_times.append(
                            cond.last_transition_time.timestamp()
                        )
                        break
            if condition_2 is None:
                if len(ready_times) == 0 and desired_replicas == 0:
                    condition_2 = condition_1
                elif len(ready_times) >= desired_replicas:
                    condition_2 = max(ready_times)
                    logger.info(
                        f"condition_2 set via pod Ready lastTransitionTime"
                        f" fallback: {condition_2}"
                    )
            if condition_3 is None and creation_times:
                condition_3 = max(creation_times)
                logger.info(
                    f"condition_3 set via pod creationTimestamp fallback: "
                    f"{condition_3}"
                )

        with open(
            "%s/rs-events-%03d.json" % (self.trial_dir, generation), "w"
        ) as f:
            json.dump(
                [
                    {"ts": ts, "rs": event["object"].to_dict()}
                    for tag, event, ts in event_list
                    if tag == "rs"
                ],
                f,
                cls=ActoEncoder,
                indent=4,
            )
        return condition_1, condition_2, condition_3

    def _measure_sts_or_ds(
        self,
        input: dict,
        generation: int,
        sts_name_f: Optional[Callable[[dict], str]],
        daemon_set_name_f: Optional[Callable[[dict], str]],
    ) -> tuple[Optional[float], Optional[float]]:
        logger = get_thread_logger(with_prefix=True)
        acto_dumps = partial(json.dumps, cls=ActoEncoder)
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
        condition_1 = None
        condition_2 = None

        if sts_name_f:
            if len(event_list) == 1:
                condition_1 = condition_2 = event_list[-1][1]
            else:
                last_revision = event_list[-1][0][
                    "object"
                ].status.update_revision
                last_spec = event_list[-1][0]["object"].to_dict()["spec"]
                last_spec_hash = hashlib.sha256(
                    json.dumps(last_spec, sort_keys=True).encode()
                ).hexdigest()
                prev_spec = None
                for event, timestamp in event_list:
                    obj_dict = event["object"].to_dict()
                    logger.info(
                        f"{event['type']} {event['object'].metadata.name} at "
                        f"{timestamp} - {datetime.fromtimestamp(timestamp)}"
                    )
                    patch = jsonpatch.JsonPatch.from_diff(
                        prev_spec, obj_dict["spec"], dumps=acto_dumps
                    )
                    logger.info(f"Patch: {patch.to_string(dumps=acto_dumps)}")
                    curr_spec = obj_dict["spec"]
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
        elif daemon_set_name_f:
            if len(event_list) == 1:
                condition_1 = condition_2 = event_list[-1][1]
            else:
                last_spec = event_list[-1][0]["object"].to_dict()["spec"]
                last_spec_hash = hashlib.sha256(
                    json.dumps(last_spec, sort_keys=True).encode()
                ).hexdigest()
                prev_obj = None
                for ds_event, timestamp in event_list:
                    obj_dict = ds_event["object"].to_dict()
                    logger.info(
                        f"{ds_event['type']} {obj_dict['metadata']['name']} at "
                        f"{timestamp} - {datetime.fromtimestamp(timestamp)}"
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

        with open(
            "%s/sts-events-%03d.json" % (self.trial_dir, generation), "w"
        ) as f:
            json.dump(
                [
                    {"ts": ts, "statefulset": sts["object"].to_dict()}
                    for sts, ts in event_list
                ],
                f,
                cls=ActoEncoder,
                indent=4,
            )
        return condition_1, condition_2

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

        return True

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

        return True

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
        try:
            for object in event_stream:
                try:
                    logging.info(f"event type: {object['type']}")
                    ts = time.time()
                    queue.put((object, ts))
                except (ValueError, AssertionError):
                    pass
        except SSLError:
            pass

    @staticmethod
    def watch_system_events_tagged(event_stream, queue: Queue, tag: str):
        """A process that watches namespaced events and tags each entry."""
        try:
            for object in event_stream:
                try:
                    logging.info(f"event type: {object['type']}, tag: {tag}")
                    ts = time.time()
                    queue.put((tag, object, ts))
                except (ValueError, AssertionError) as e:
                    logging.info("failed to process event due to %s", str(e))
        except SSLError:
            pass

    @staticmethod
    def wait_for_vdeployment_converge(
        input: dict,
        apiclient: kubernetes.client.ApiClient,
        namespace: str,
        vdeployment_name: str,
    ) -> list:
        """Watch VReplicaSet and pod events for a VDeployment until pods are ready.

        Returns a list of (tag, event, timestamp) tuples where tag is "vrs" for
        VReplicaSet events and "pod" for pod events.  VReplicaSet events are
        filtered to only those owned by the given VDeployment.
        """
        custom_api = kubernetes.client.CustomObjectsApi(apiclient)
        core_v1_api = kubernetes.client.CoreV1Api(apiclient)
        watch_vrs = kubernetes.watch.Watch()
        watch_pods = kubernetes.watch.Watch()

        updates: list = []
        updates_queue: Queue = Queue(maxsize=0)

        vrs_stream = watch_vrs.stream(
            func=custom_api.list_namespaced_custom_object,
            group="anvil.dev",
            version="v1",
            namespace=namespace,
            plural="vreplicasets",
        )
        pod_stream = watch_pods.stream(
            func=core_v1_api.list_namespaced_pod,
            namespace=namespace,
        )

        timer_hard_timeout = acto_timer.ActoTimer(900, updates_queue, "timeout")
        vrs_watch_process = Process(
            target=MeasurementRunner.watch_system_events_tagged,
            args=(vrs_stream, updates_queue, "vrs"),
        )
        pod_watch_process = Process(
            target=MeasurementRunner.watch_system_events_tagged,
            args=(pod_stream, updates_queue, "pod"),
        )

        timer_hard_timeout.start()
        vrs_watch_process.start()
        pod_watch_process.start()

        while True:
            try:
                item = updates_queue.get(timeout=120)
                if isinstance(item, str) and item == "timeout":
                    break
                tag, event, ts = item
                if tag == "vrs":
                    owner_refs = (
                        event["object"]
                        .get("metadata", {})
                        .get("ownerReferences")
                        or []
                    )
                    if any(
                        ref.get("kind") == "VDeployment"
                        and ref.get("name") == vdeployment_name
                        for ref in owner_refs
                    ):
                        updates.append((tag, event, ts))
                else:
                    updates.append((tag, event, ts))
            except queue.Empty:
                if check_pods_ready(input, apiclient, namespace):
                    break
                else:
                    logging.info("pods not ready")
                    continue

        vrs_stream.close()
        pod_stream.close()
        timer_hard_timeout.cancel()
        vrs_watch_process.terminate()
        pod_watch_process.terminate()

        return updates

    @staticmethod
    def wait_for_deployment_converge(
        input: dict,
        apiclient: kubernetes.client.ApiClient,
        namespace: str,
        deployment_name: str,
    ) -> list:
        """Watch ReplicaSet and pod events for a Deployment until pods are ready.

        Returns a list of (tag, event, timestamp) tuples where tag is "rs" for
        ReplicaSet events and "pod" for pod events.  ReplicaSet events are
        filtered to only those owned by the given Deployment.
        """
        apps_v1_api = kubernetes.client.AppsV1Api(apiclient)
        core_v1_api = kubernetes.client.CoreV1Api(apiclient)
        watch_rs = kubernetes.watch.Watch()
        watch_pods = kubernetes.watch.Watch()

        updates: list = []
        updates_queue: Queue = Queue(maxsize=0)

        rs_stream = watch_rs.stream(
            func=apps_v1_api.list_namespaced_replica_set,
            namespace=namespace,
        )
        pod_stream = watch_pods.stream(
            func=core_v1_api.list_namespaced_pod,
            namespace=namespace,
        )

        timer_hard_timeout = acto_timer.ActoTimer(900, updates_queue, "timeout")
        rs_watch_process = Process(
            target=MeasurementRunner.watch_system_events_tagged,
            args=(rs_stream, updates_queue, "rs"),
        )
        pod_watch_process = Process(
            target=MeasurementRunner.watch_system_events_tagged,
            args=(pod_stream, updates_queue, "pod"),
        )

        timer_hard_timeout.start()
        rs_watch_process.start()
        pod_watch_process.start()

        while True:
            try:
                item = updates_queue.get(timeout=120)
                if isinstance(item, str) and item == "timeout":
                    break
                tag, event, ts = item
                if tag == "rs":
                    owner_refs = event["object"].metadata.owner_references or []
                    if any(
                        ref.kind == "Deployment" and ref.name == deployment_name
                        for ref in owner_refs
                    ):
                        updates.append((tag, event, ts))
                else:
                    updates.append((tag, event, ts))
            except queue.Empty:
                if check_pods_ready(input, apiclient, namespace):
                    break
                else:
                    logging.info("pods not ready")
                    continue

        rs_stream.close()
        pod_stream.close()
        timer_hard_timeout.cancel()
        rs_watch_process.terminate()
        pod_watch_process.terminate()

        return updates

    @staticmethod
    def rabbitmq_sts_name(input: dict):
        return f"{input['metadata']['name']}-server"

    @staticmethod
    def vdeployment_name(input: dict):
        return input["metadata"]["name"]

    @staticmethod
    def deployment_name(input: dict):
        return input["metadata"]["name"]
