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
    """Custom oracle for checking Cassandra users"""

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

        current_users = []
        prev_users =[]
        if ("users" in snapshot.input_cr["spec"]):
            current_users = snapshot.input_cr["spec"]["users"]
        
        if ("users" in prev_snapshot.input_cr["spec"]):
            prev_users = prev_snapshot.input_cr["spec"]["users"]

        # Get the configuration from the cqlsh
        sts_list = self.oracle_handle.get_stateful_sets()
        pod_list = self.oracle_handle.get_pods_in_stateful_set(sts_list[0])

        if len(pod_list) == 0:
            return None

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
                "LIST USERS;",
            ],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="Cassandra users check failed")
        
        logger.info("Cassandra users check output: %s", p.stdout)

        cass_output = p.stdout.split("\n")
        lines = cass_output[3:-2]

        system_users = []
        for line in lines:
            if line.strip():
                system_users.append(line.split("|")[0].strip())

        for user in current_users:
            secret = core_v1.read_namespaced_secret(
                user["secretName"], self.oracle_handle.namespace
            ).data
            if not secret or "username" not in secret or "password" not in secret:
                return OracleResult(
                    message=f"Secret {user['secretName']} not found or missing username/password"
                )
            username = base64.b64decode(secret["username"]).decode("utf-8")

            if username not in system_users:
                return OracleResult(
                    message=f"User {username} is missing in Cassandra config"
                )
        for user in prev_users:
            secret = core_v1.read_namespaced_secret(
                user["secretName"], self.oracle_handle.namespace
            ).data
            if not secret or "username" not in secret or "password" not in secret:
                return OracleResult(
                    message=f"Secret {user['secretName']} not found or missing username/password"
                )
            username = base64.b64decode(secret["username"]).decode("utf-8")
            if user["secretName"] not in current_users and user["secretName"] in system_users:
                return OracleResult(
                    message=f"User {user} should be removed from Cassandra config"
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
            namespace=self.oracle_handle.namespace,
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
