"""This module generates Deployment inputs from VDeployment Anvil inputs."""

import os

import jsonpatch
import yaml

from acto.post_process.post_chain_inputs import ChainInputs


class VDeploymentInputGenerator(ChainInputs):
    """Generates serialized inputs for the VDeployment controller and converts
    them to equivalent native Kubernetes Deployment inputs."""

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
                    yaml.dump(
                        VDeploymentInputGenerator.convert(entry["input"]), f
                    )
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
        """Convert a VDeployment CR to an equivalent Kubernetes Deployment."""
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": anvil_cr["metadata"],
            "spec": anvil_cr["spec"],
        }
