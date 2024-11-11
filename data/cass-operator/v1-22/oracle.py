import base64
import re
from typing import Optional

import kubernetes

from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger


class CassandraConfigChecker(CheckerInterface):
    """Custom oracle for checking Cassandra config"""

    name = "cassandra-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra config"""
        logger = get_thread_logger()

        if (
            "config" in snapshot.input_cr["spec"]
            and "cassandra-yaml" in snapshot.input_cr["spec"]["config"]
        ):
            cassandra_yaml = snapshot.input_cr["spec"]["config"][
                "cassandra-yaml"
            ]
        else:
            return None

        # Get the configuration from the cqlsh
        sts_list = self.oracle_handle.get_stateful_sets()
        pod_list = self.oracle_handle.get_pods_in_stateful_set(sts_list[0])

        core_v1 = kubernetes.client.CoreV1Api(self.oracle_handle.k8s_client)

        secret = core_v1.read_namespaced_secret(
            "development-superuser", self.oracle_handle.namespace
        ).data

        username = base64.b64decode(secret["username"]).decode("utf-8")
        password = base64.b64decode(secret["password"]).decode("utf-8")

        pod = pod_list[0]
        p = self.oracle_handle.kubectl_client.exec(
            pod.metadata.name,
            pod.metadata.namespace,
            [
                "cqlsh",
                "-u",
                username,
                "-p",
                password,
                "-e",
                "SELECT (name,value) FROM system_views.settings",
            ],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="Cassandra config check failed")

        cass_output = p.stdout.split("\n")
        lines = cass_output[3:-3]

        config_data = {}
        for line in lines:
            matches = re.match(r"\s*\((\w+), '?(\w+)'?\)", line)
            if matches:
                key = matches.group(1)
                value = matches.group(2)
                config_data[key] = value
            else:
                logger.error("Failed to parse line: %s", line)

        for key, value in cassandra_yaml.items():
            if key not in config_data:
                return OracleResult(
                    message=f"Key {key} is missing in Cassandra config"
                )
            if config_data[key] != value:
                return OracleResult(
                    message=f"Value of key {key} is incorrect in Cassandra config"
                )

        return None


CUSTOM_CHECKER: list[type] = [CassandraConfigChecker]
