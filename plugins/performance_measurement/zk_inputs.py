"""This module generates ZooKeeper CRs from Anvil inputs."""

import os
import sys

import jsonpatch
import yaml

from acto.post_process.post_chain_inputs import ChainInputs


class ZooKeeperInputGenerator(ChainInputs):
    def serialize(self, output_dir: str):
        previous_input = {}
        index = 0
        anvil_input_dir = os.path.join(output_dir, "anvil_inputs")
        reference_input_dir = os.path.join(output_dir, "reference")
        os.makedirs(anvil_input_dir, exist_ok=True)
        os.makedirs(reference_input_dir, exist_ok=True)
        for input in self.all_inputs:
            print(f"{input['trial']}")
            input["input"]["spec"][
                "image"
            ] = "ghcr.io/xlab-uiuc/zookeeper:0.2.14"
            patch = jsonpatch.JsonPatch.from_diff(
                previous_input, input["input"]
            )
            if patch:
                skip_input = False
                for ops in patch:
                    if "/spec/conf" in ops["path"]:
                        print(ops)
                        skip_input = True
                        break

                if skip_input:
                    continue
                with open(
                    os.path.join(anvil_input_dir, f"input-{index:03d}.yaml"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    yaml.dump(input["input"], f)
                with open(
                    os.path.join(
                        reference_input_dir, f"input-{index:03d}.yaml"
                    ),
                    "w",
                    encoding="utf-8",
                ) as f:
                    yaml.dump(
                        ZooKeeperInputGenerator.convert(input["input"]), f
                    )
                with open(
                    os.path.join(output_dir, f"input-{index:03d}.patch"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(str(patch))
                previous_input = input["input"]
                index += 1

    @staticmethod
    def convert(anvil_cr: dict) -> dict:
        zk_cr = {
            "apiVersion": "zookeeper.pravega.io/v1beta1",
            "kind": "ZookeeperCluster",
            "metadata": {"name": "test-cluster"},
            "spec": {},
        }

        if "affinity" in anvil_cr["spec"]:
            if "pod" not in zk_cr["spec"]:
                zk_cr["spec"]["pod"] = {}
            zk_cr["spec"]["pod"]["affinity"] = anvil_cr["spec"]["affinity"]

        if "annotations" in anvil_cr["spec"]:
            if "pod" not in zk_cr["spec"]:
                zk_cr["spec"]["pod"] = {}
            zk_cr["spec"]["pod"]["annotations"] = anvil_cr["spec"][
                "annotations"
            ]

        if "conf" in anvil_cr["spec"]:
            zk_cr["spec"]["config"] = anvil_cr["spec"]["conf"].copy()
            if "quorumListenOnAllIps" in zk_cr["spec"]["config"]:
                zk_cr["spec"]["config"]["quorumListenOnAllIPs"] = zk_cr["spec"][
                    "config"
                ].pop("quorumListenOnAllIps")

        if "image" in anvil_cr["spec"]:
            repository = anvil_cr["spec"]["image"].split(":")[0]
            tag = anvil_cr["spec"]["image"].split(":")[1]
            zk_cr["spec"]["image"] = {"repository": repository, "tag": tag}

        if "labels" in anvil_cr["spec"]:
            if "pod" not in zk_cr["spec"]:
                zk_cr["spec"]["pod"] = {}
            zk_cr["spec"]["pod"]["labels"] = anvil_cr["spec"]["labels"]

        if "nodeSelector" in anvil_cr["spec"]:
            if "pod" not in zk_cr["spec"]:
                zk_cr["spec"]["pod"] = {}
            zk_cr["spec"]["pod"]["nodeSelector"] = anvil_cr["spec"][
                "nodeSelector"
            ]

        if (
            "persistence" in anvil_cr["spec"]
            and anvil_cr["spec"]["persistence"]["enabled"]
        ):
            if "persistence" not in zk_cr["spec"]:
                zk_cr["spec"]["persistence"] = {"spec": {}}

            if "storageClassName" in anvil_cr["spec"]["persistence"]:
                zk_cr["spec"]["persistence"]["spec"][
                    "storageClassName"
                ] = anvil_cr["spec"]["persistence"]["storageClassName"]

            if "storageSize" in anvil_cr["spec"]["persistence"]:
                zk_cr["spec"]["persistence"]["spec"]["resources"] = {
                    "requests": {
                        "storage": anvil_cr["spec"]["persistence"][
                            "storageSize"
                        ]
                    }
                }

        port_name_map = {
            "adminServer": "admin-server",
            "client": "client",
            "leaderElection": "leader-election",
            "metrics": "metrics",
            "quorum": "quorum",
        }

        if "ports" in anvil_cr["spec"]:
            zk_cr["spec"]["ports"] = []
            for port_name, port_number in anvil_cr["spec"]["ports"].items():
                zk_cr["spec"]["ports"].append(
                    {
                        "containerPort": port_number,
                        "name": port_name_map[port_name],
                    }
                )

        if "replicas" in anvil_cr["spec"]:
            zk_cr["spec"]["replicas"] = anvil_cr["spec"]["replicas"]

        if "resources" in anvil_cr["spec"]:
            if "pod" not in zk_cr["spec"]:
                zk_cr["spec"]["pod"] = {}
            zk_cr["spec"]["pod"]["resources"] = anvil_cr["spec"]["resources"]

        if "tolerations" in anvil_cr["spec"]:
            if "pod" not in zk_cr["spec"]:
                zk_cr["spec"]["pod"] = {}
            zk_cr["spec"]["pod"]["tolerations"] = anvil_cr["spec"][
                "tolerations"
            ]

        return zk_cr
