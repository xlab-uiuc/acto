import json
from typing import Callable, Optional

from acto.checker.checker import CheckerInterface
from acto.common import canonicalize
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot


class ZookeeperOracle(CheckerInterface):
    """Custom oracle for checking Zookeeper cluster health"""

    name = "custom"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Checks the health of the Zookeeper cluster"""
        _, _, _ = generation, snapshot, prev_snapshot

        handle = self.oracle_handle

        cr = handle.get_cr()
        if "config" in cr["spec"]:
            config = cr["spec"]["config"]
            if (
                "additionalConfig" in config
                and config["additionalConfig"] is not None
            ):
                for key, value in config["additionalConfig"].items():
                    config[key] = value
                del config["additionalConfig"]
        else:
            config = None

        sts_list = handle.get_stateful_sets()

        if len(sts_list) != 1:
            return OracleResult(
                message="Zookeeper cluster has more than one stateful set",
            )

        pod_list = handle.get_pods_in_stateful_set(sts_list[0])

        leaders = 0
        for pod in pod_list:
            if pod.status.pod_ip is None:
                return OracleResult(
                    message="Zookeeper pod does not have an IP assigned",
                )
            p = handle.kubectl_client.exec(
                pod.metadata.name,
                pod.metadata.namespace,
                ["curl", "http://" + pod.status.pod_ip + ":8080/commands/ruok"],
                capture_output=True,
                text=True,
            )
            if p.returncode != 0:
                return OracleResult(message="Zookeeper pod is not responding")
            else:
                result = json.loads(p.stdout)
                if result["error"] is not None:
                    return OracleResult(
                        message="Zookeeper cluster curl has error "
                        + result["error"],
                    )

            p = handle.kubectl_client.exec(
                pod.metadata.name,
                pod.metadata.namespace,
                ["curl", "http://" + pod.status.pod_ip + ":8080/commands/stat"],
                capture_output=True,
                text=True,
            )
            if p.returncode != 0:
                return OracleResult(message="Zookeeper pod is not responding")
            else:
                result = json.loads(p.stdout)
                if result["error"] is not None:
                    return OracleResult(
                        message="Zookeeper cluster curl has error "
                        + result["error"],
                    )
                elif result["server_stats"]["server_state"] == "leader":
                    leaders += 1

            if config is not None:
                p = handle.kubectl_client.exec(
                    pod.metadata.name,
                    pod.metadata.namespace,
                    [
                        "curl",
                        "http://" + pod.status.pod_ip + ":8080/commands/conf",
                    ],
                    capture_output=True,
                    text=True,
                )

                if p.returncode != 0:
                    return OracleResult(
                        message="Zookeeper pod is not responding",
                    )
                else:
                    result = json.loads(p.stdout)
                    if result["error"] is not None:
                        return OracleResult(
                            message="Zookeeper cluster curl has error "
                            + result["error"],
                        )

                    for key, value in config.items():
                        canonicalize_key = canonicalize(key)
                        if canonicalize_key not in result:
                            return OracleResult(
                                message="Zookeeper config does not contain key "
                                + key,
                            )
                        elif result[canonicalize_key] != value:
                            return OracleResult(
                                message="Zookeeper cluster has incorrect config",
                            )

        if leaders > 1:
            return OracleResult(
                message="Zookeeper cluster has more than one leader",
            )

        p = handle.kubectl_client.exec(
            "zkapp",
            handle.namespace,
            ["request"],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="Zookeeper app request failed")
        elif p.stdout != "test":
            return OracleResult(
                message=f"Zookeeper app request result wrong {p.stdout}",
            )

        return None


def deploy_zk_app(handle: OracleHandle):
    """Deploys a Zookeeper app for testing purposes"""
    handle.kubectl_client.kubectl(
        [
            "run",
            "zkapp",
            "--image=tylergu1998/zkapp:v1",
            "-l",
            "acto/tag=custom-oracle",
            "-n",
            handle.namespace,
        ]
    )


CUSTOM_CHECKER: type[CheckerInterface] = ZookeeperOracle
ON_INIT: Callable = deploy_zk_app
