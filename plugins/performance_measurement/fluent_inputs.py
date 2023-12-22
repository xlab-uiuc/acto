import os
import sys
from typing import Any, Dict

import jsonpatch
import yaml

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from acto.post_process.post_chain_inputs import ChainInputs


class FluentInputGenerator(ChainInputs):
    def serialize(self, output_dir: str):
        previous_input: Dict[str, Any] = {}
        index = 0
        anvil_input_dir = os.path.join(output_dir, "anvil_inputs")
        reference_input_dir = os.path.join(output_dir, "reference")
        os.makedirs(anvil_input_dir, exist_ok=True)
        os.makedirs(reference_input_dir, exist_ok=True)
        print(f"Serializing to {output_dir}")
        for input_ in self.all_inputs:
            if "envVars" in input_["input"]["spec"]:
                del input_["input"]["spec"]["envVars"]
            if "initContainers" in input_["input"]["spec"]:
                del input_["input"]["spec"]["initContainers"]
            if "affinity" in input_["input"]["spec"]:
                del input_["input"]["spec"]["affinity"]
            if "command" in input_["input"]["spec"]:
                del input_["input"]["spec"]["command"]
            if "nodeSelector" in input_["input"]["spec"]:
                del input_["input"]["spec"]["nodeSelector"]
            if "readinessProbe" in input_["input"]["spec"]:
                del input_["input"]["spec"]["readinessProbe"]
            if "priorityClassName" in input_["input"]["spec"]:
                del input_["input"]["spec"]["priorityClassName"]
            if "schedulerName" in input_["input"]["spec"]:
                del input_["input"]["spec"]["schedulerName"]
            if "runtimeClassName" in input_["input"]["spec"]:
                del input_["input"]["spec"]["runtimeClassName"]
            if "serviceAnnotations" in input_["input"]["spec"]:
                del input_["input"]["spec"]["serviceAnnotations"]
            if "serviceLabels" in input_["input"]["spec"]:
                del input_["input"]["spec"]["serviceLabels"]
            if "serviceSelector" in input_["input"]["spec"]:
                del input_["input"]["spec"]["serviceSelector"]
            if "disableLogVolumes" in input_["input"]["spec"]:
                del input_["input"]["spec"]["disableLogVolumes"]
            if (
                "resources" in input_["input"]["spec"]
                and "claims" in input_["input"]["spec"]["resources"]
            ):
                del input_["input"]["spec"]["resources"]["claims"]
            input_["input"]["spec"][
                "image"
            ] = "ghcr.io/xlab-uiuc/fluent-bit:v2.1.7"
            patch = jsonpatch.JsonPatch.from_diff(
                previous_input, input_["input"]
            )
            if patch:
                skip_input = False
                if skip_input:
                    continue
                print(patch)
                with open(
                    os.path.join(anvil_input_dir, f"input-{index:03d}.yaml"),
                    "w",
                ) as f:
                    yaml.dump(input_["input"], f)
                with open(
                    os.path.join(
                        reference_input_dir, f"input-{index:03d}.yaml"
                    ),
                    "w",
                ) as f:
                    yaml.dump(FluentInputGenerator.convert(input_["input"]), f)
                with open(
                    os.path.join(output_dir, f"input-{index:03d}.patch"), "w"
                ) as f:
                    f.write(str(patch))
                previous_input = input_["input"]
                index += 1

    @staticmethod
    def convert(anvil_cr: dict) -> dict:
        fluent_cr: Dict[str, Any] = {
            "apiVersion": "fluentbit.fluent.io/v1alpha2",
            "kind": "FluentBit",
            "metadata": {
                "name": "test-cluster",
                "labels": {"app.kubernetes.io/name": "fluent-bit"},
            },
            "spec": {},
        }

        # affinity
        if "affinity" in anvil_cr["spec"]:
            fluent_cr["spec"]["affinity"] = anvil_cr["spec"]["affinity"]

        # annotations
        if "annotations" in anvil_cr["spec"]:
            fluent_cr["spec"]["annotations"] = anvil_cr["spec"]["annotations"]

        # args
        if "args" in anvil_cr["spec"]:
            fluent_cr["spec"]["args"] = anvil_cr["spec"]["args"]

        # command
        if "command" in anvil_cr["spec"]:
            fluent_cr["spec"]["command"] = anvil_cr["spec"]["command"]

        # containerLogRealPath
        if "containerLogRealPath" in anvil_cr["spec"]:
            fluent_cr["spec"]["containerLogRealPath"] = anvil_cr["spec"][
                "containerLogRealPath"
            ]

        # containerSecurityContext
        if "containerSecurityContext" in anvil_cr["spec"]:
            fluent_cr["spec"]["containerSecurityContext"] = anvil_cr["spec"][
                "containerSecurityContext"
            ]

        # disableLogVolumes - not found

        # dnsPolicy
        if "dnsPolicy" in anvil_cr["spec"]:
            fluent_cr["spec"]["dnsPolicy"] = anvil_cr["spec"]["dnsPolicy"]

        # envVars
        if "envVars" in anvil_cr["spec"]:
            fluent_cr["spec"]["envVars"] = anvil_cr["spec"]["envVars"]

        # fluentBitConfigName
        if "fluentBitConfigName" in anvil_cr["spec"]:
            fluent_cr["spec"]["fluentBitConfigName"] = anvil_cr["spec"][
                "fluentBitConfigName"
            ]

        # hostNetwork
        if "hostNetwork" in anvil_cr["spec"]:
            fluent_cr["spec"]["hostNetwork"] = anvil_cr["spec"]["hostNetwork"]

        # image
        if "image" in anvil_cr["spec"]:
            fluent_cr["spec"]["image"] = anvil_cr["spec"]["image"]

        # imagePullPolicy
        if "imagePullPolicy" in anvil_cr["spec"]:
            fluent_cr["spec"]["imagePullPolicy"] = anvil_cr["spec"][
                "imagePullPolicy"
            ]

        # imagePullSecrets
        if "imagePullSecrets" in anvil_cr["spec"]:
            fluent_cr["spec"]["imagePullSecrets"] = anvil_cr["spec"][
                "imagePullSecrets"
            ]

        # initContainers
        if "initContainers" in anvil_cr["spec"]:
            fluent_cr["spec"]["initContainers"] = anvil_cr["spec"][
                "initContainers"
            ]

        # internalMountPropagation
        if "internalMountPropagation" in anvil_cr["spec"]:
            fluent_cr["spec"]["internalMountPropagation"] = anvil_cr["spec"][
                "internalMountPropagation"
            ]

        # labels
        if "labels" in anvil_cr["spec"]:
            fluent_cr["spec"]["labels"] = anvil_cr["spec"]["labels"]

        # metricsPort
        if "metricsPort" in anvil_cr["spec"]:
            fluent_cr["spec"]["metricsPort"] = anvil_cr["spec"]["metricsPort"]

        # nodeSelector
        if "nodeSelector" in anvil_cr["spec"]:
            fluent_cr["spec"]["nodeSelector"] = anvil_cr["spec"]["nodeSelector"]

        # ports:
        if "ports" in anvil_cr["spec"]:
            fluent_cr["spec"]["ports"] = anvil_cr["spec"]["ports"]

        # positionDB
        if "positionDB" in anvil_cr["spec"]:
            fluent_cr["spec"]["positionDB"] = anvil_cr["spec"]["positionDB"]

        # priorityClassName
        if "priorityClassName" in anvil_cr["spec"]:
            fluent_cr["spec"]["priorityClassName"] = anvil_cr["spec"][
                "priorityClassName"
            ]

        # readinessProbe
        if "readinessProbe" in anvil_cr["spec"]:
            fluent_cr["spec"]["readinessProbe"] = anvil_cr["spec"][
                "readinessProbe"
            ]

        # resources
        if "resources" in anvil_cr["spec"]:
            fluent_cr["spec"]["resources"] = anvil_cr["spec"]["resources"]

        # runtimeClassName
        if "runtimeClassName" in anvil_cr["spec"]:
            fluent_cr["spec"]["runtimeClassName"] = anvil_cr["spec"][
                "runtimeClassName"
            ]

        # schedulerName
        if "schedulerName" in anvil_cr["spec"]:
            fluent_cr["spec"]["schedulerName"] = anvil_cr["spec"][
                "schedulerName"
            ]

        # securityContext
        if "securityContext" in anvil_cr["spec"]:
            fluent_cr["spec"]["securityContext"] = anvil_cr["spec"][
                "securityContext"
            ]

        # serviceAccountAnnotations
        if "serviceAccountAnnotations" in anvil_cr["spec"]:
            fluent_cr["spec"]["serviceAccountAnnotations"] = anvil_cr["spec"][
                "serviceAccountAnnotations"
            ]

        # tolerations
        if "tolerations" in anvil_cr["spec"]:
            fluent_cr["spec"]["tolerations"] = anvil_cr["spec"]["tolerations"]

        # serviceAnnotations
        # serviceLabels
        # serviceSelector
        # not found

        # volumeMounts
        if "volumeMounts" in anvil_cr["spec"]:
            fluent_cr["spec"]["volumeMounts"] = anvil_cr["spec"]["volumeMounts"]

        # volumes
        if "volumes" in anvil_cr["spec"]:
            fluent_cr["spec"]["volumes"] = anvil_cr["spec"]["volumes"]

        return fluent_cr
