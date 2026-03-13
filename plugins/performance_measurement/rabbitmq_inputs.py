"""This module contains the input generator for the rabbitmq controller."""

import os
import sys

import jsonpatch
import yaml

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from acto.post_process.post_chain_inputs import ChainInputs


class RabbitMQInputGenerator(ChainInputs):
    def serialize(self, output_dir: str):
        previous_input: dict = {}
        index = 0
        anvil_input_dir = os.path.join(output_dir, "anvil_inputs")
        reference_input_dir = os.path.join(output_dir, "reference")
        os.makedirs(anvil_input_dir, exist_ok=True)
        os.makedirs(reference_input_dir, exist_ok=True)
        print(f"Serializing to {output_dir}")
        for entry in self.all_inputs:
            print(f"{entry['trial']}")
            entry["input"]["spec"][
                "image"
            ] = "ghcr.io/xlab-uiuc/rabbitmq:3.11.10-management"
            entry["input"]["spec"]["replicas"] = 3
            if (
                "resources" in entry["input"]["spec"]
                and "claims" in entry["input"]["spec"]["resources"]
            ):
                del entry["input"]["spec"]["resources"]["claims"]
            if (
                "resources" not in entry["input"]["spec"]
                or entry["input"]["spec"]["resources"] is None
            ):
                entry["input"]["spec"]["resources"] = {
                    "limits": {"cpu": "2", "memory": "2Gi"},
                    "requests": {"cpu": "1", "memory": "2Gi"},
                }
            else:
                if "limits" not in entry["input"]["spec"]["resources"]:
                    entry["input"]["spec"]["resources"]["limits"] = {
                        "cpu": "2",
                        "memory": "2Gi",
                    }
                elif "cpu" not in entry["input"]["spec"]["resources"]["limits"]:
                    entry["input"]["spec"]["resources"]["limits"]["cpu"] = "2"
                elif (
                    "memory"
                    not in entry["input"]["spec"]["resources"]["limits"]
                ):
                    entry["input"]["spec"]["resources"]["limits"][
                        "memory"
                    ] = "2Gi"

                if "requests" not in entry["input"]["spec"]["resources"]:
                    entry["input"]["spec"]["resources"]["requests"] = {
                        "cpu": "1",
                        "memory": "2Gi",
                    }
                elif (
                    "cpu" not in entry["input"]["spec"]["resources"]["requests"]
                ):
                    entry["input"]["spec"]["resources"]["requests"]["cpu"] = "1"
                elif (
                    "memory"
                    not in entry["input"]["spec"]["resources"]["requests"]
                ):
                    entry["input"]["spec"]["resources"]["requests"][
                        "memory"
                    ] = "2Gi"

            patch = jsonpatch.JsonPatch.from_diff(
                previous_input, entry["input"]
            )
            if patch:
                print(patch)
                with open(
                    os.path.join(anvil_input_dir, f"input-{index:03d}.yaml"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    yaml.dump(entry["input"], f)
                with open(
                    os.path.join(
                        reference_input_dir, f"input-{index:03d}.yaml"
                    ),
                    "w",
                    encoding="utf-8",
                ) as f:
                    yaml.dump(RabbitMQInputGenerator.convert(entry["input"]), f)
                with open(
                    os.path.join(output_dir, f"input-{index:03d}.patch"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(str(patch))
                previous_input = entry["input"]
                index += 1

    @staticmethod
    def convert(anvil_cr: dict) -> dict:
        rabbitmq_cr = {
            "apiVersion": "rabbitmq.com/v1beta1",
            "kind": "RabbitmqCluster",
            "metadata": {
                "name": "test-cluster",
                "namespace": "rabbitmq-system",
            },
            "spec": {},
        }

        if "affinity" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["affinity"] = anvil_cr["spec"]["affinity"]

        if "annotations" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["override"] = {
                "statefulSet": {
                    "spec": {
                        "template": {
                            "metadata": {
                                "annotations": anvil_cr["spec"]["annotations"]
                            }
                        }
                    }
                }
            }

        if "image" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["image"] = anvil_cr["spec"]["image"]

        if "labels" in anvil_cr["spec"]:
            if "override" not in rabbitmq_cr["spec"]:
                rabbitmq_cr["spec"]["override"] = {}
            if "statefulSet" not in rabbitmq_cr["spec"]["override"]:
                rabbitmq_cr["spec"]["override"]["statefulSet"] = {}
            if "spec" not in rabbitmq_cr["spec"]["override"]["statefulSet"]:
                rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"] = {}
            if (
                "template"
                not in rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"]
            ):
                rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"][
                    "template"
                ] = {}
            if (
                "metadata"
                not in rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"][
                    "template"
                ]
            ):
                rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"][
                    "template"
                ]["metadata"] = {}
            rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"]["template"][
                "metadata"
            ]["labels"] = anvil_cr["spec"]["labels"]

        if "persistence" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["persistence"] = anvil_cr["spec"]["persistence"]

        if "persistentVolumeClaimRetentionPolicy" in anvil_cr["spec"]:
            if "override" not in rabbitmq_cr["spec"]:
                rabbitmq_cr["spec"]["override"] = {}
            if "statefulSet" not in rabbitmq_cr["spec"]["override"]:
                rabbitmq_cr["spec"]["override"]["statefulSet"] = {}
            if "spec" not in rabbitmq_cr["spec"]["override"]["statefulSet"]:
                rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"] = {}
            rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"][
                "persistentVolumeClaimRetentionPolicy"
            ] = anvil_cr["spec"]["persistentVolumeClaimRetentionPolicy"]

        if "podManagementPolicy" in anvil_cr["spec"]:
            if "override" not in rabbitmq_cr["spec"]:
                rabbitmq_cr["spec"]["override"] = {}
            if "statefulSet" not in rabbitmq_cr["spec"]["override"]:
                rabbitmq_cr["spec"]["override"]["statefulSet"] = {}
            if "spec" not in rabbitmq_cr["spec"]["override"]["statefulSet"]:
                rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"] = {}
            rabbitmq_cr["spec"]["override"]["statefulSet"]["spec"][
                "podManagementPolicy"
            ] = anvil_cr["spec"]["podManagementPolicy"]

        if "rabbitmqConfig" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["rabbitmq"] = anvil_cr["spec"]["rabbitmqConfig"]
            if "advancedConfig" in rabbitmq_cr["spec"]["rabbitmq"]:
                del rabbitmq_cr["spec"]["rabbitmq"]["advancedConfig"]
            if "envConfig" in rabbitmq_cr["spec"]["rabbitmq"]:
                del rabbitmq_cr["spec"]["rabbitmq"]["envConfig"]

        if "replicas" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["replicas"] = anvil_cr["spec"]["replicas"]

        if "resources" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["resources"] = anvil_cr["spec"]["resources"]

        if "tolerations" in anvil_cr["spec"]:
            rabbitmq_cr["spec"]["tolerations"] = anvil_cr["spec"]["tolerations"]

        return rabbitmq_cr
