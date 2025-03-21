import base64
import datetime
import re
from typing import Callable, Optional

import kubernetes

# pylint: disable=import-error
from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger

# pylint: enable=import-error


class CassandraConfigChecker(CheckerInterface):
    """Custom oracle for checking Cassandra config"""

    name = "cassandra-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle
        self._previous_ts: Optional[datetime.datetime] = None

    def __check_config(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra config"""
        _, _ = generation, prev_snapshot
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
            line = line.strip()
            matches = re.match(r"\s*\('(.*)', (None|'(.*)')\)", line)
            if matches:
                key = matches.group(1)
                if matches.group(3):
                    value = matches.group(3)
                    if re.match(r"^-?\d+(?:\.\d+)?$", value):
                        value = float(value)
                    elif re.match(r"true|false", value):
                        value = value == "true"
                else:
                    value = None

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

    def __check_availability(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra writer availability rate parsing its logs"""
        _, _, _ = generation, snapshot, prev_snapshot
        logger = get_thread_logger()

        v1 = kubernetes.client.CoreV1Api(self.oracle_handle.k8s_client)
        now = datetime.datetime.now()
        since_seconds: Optional[int] = (
            None
            if self._previous_ts is None
            else int((now - self._previous_ts).total_seconds())
        )
        logs = v1.read_namespaced_pod_log(
            name="cassandra-writer",
            namespace="acto-namespace",
            container="cassandra-writer",
            since_seconds=since_seconds,
        ).split("\n")
        self._previous_ts = now

        min_avail_rate: Optional[float] = None
        for line in logs:
            match = re.search(r"TS: \[(.*?)\].*?Success Rate: \[(.*?)\]", line)
            if match:
                _ = match.group(1)
                success_rate = float(match.group(2))
                min_avail_rate = (
                    success_rate
                    if min_avail_rate is None
                    else min(min_avail_rate, success_rate)
                )

                if float(success_rate) < 0.9:
                    return OracleResult(
                        message="Cassandra writer availability rate is below 90%"
                    )
            else:
                logger.warning(
                    "Unable to parse Cassandra writer log line: %s", line
                )
                continue

        if min_avail_rate is not None:
            logger.info(
                "Cassandra writer lowest availability rate: %f", min_avail_rate
            )
        else:
            logger.error("Cassandra writer availability rate not found")

        return None

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra config and availability"""
        if result := self.__check_config(generation, snapshot, prev_snapshot):
            return result
        if result := self.__check_availability(
            generation, snapshot, prev_snapshot
        ):
            return result
        return None


def deploy_writer(handle: OracleHandle):
    """Deploy the Writer Pod for Oracle"""
    p = handle.kubectl_client.kubectl(
        [
            "apply",
            "-f",
            "data/cass-operator/v1-22/writer_pod.yaml",
            "-n",
            handle.namespace,
        ]
    )
    if p.returncode != 0:
        raise RuntimeError("Failed to deploy the writer pod", p.stderr)


CUSTOM_CHECKER: type[CheckerInterface] = CassandraConfigChecker
ON_INIT: Callable = deploy_writer
