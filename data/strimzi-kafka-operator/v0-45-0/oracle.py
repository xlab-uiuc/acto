import datetime
import re
from typing import Callable, Optional

import kubernetes
import yaml

# pylint: disable=import-error
from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger

# pylint: enable=import-error


class KafkaConfigChecker(CheckerInterface):
    """Custom oracle for checking Kafka config"""

    name = "kafka-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle
        self._previous_ts: Optional[datetime.datetime] = None

    def __check_config(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Kafka config"""
        _, _ = generation, prev_snapshot
        logger = get_thread_logger()
        logger.info("Checking Kafka config")
        if (
            "kafka" in snapshot.input_cr["spec"]
            and "config" in snapshot.input_cr["spec"]["kafka"]
        ):
            kafka_config = yaml.load(
                snapshot.input_cr["spec"]["kafka"]["config"],
                Loader=yaml.FullLoader,
            )
        else:
            return None

        pod_name = "test-cluster-dual-role-0"

        p = self.oracle_handle.kubectl_client.exec(
            pod_name,
            "acto-namespace",
            [
                "./bin/kafka-configs.sh",
                "--describe",
                "--bootstrap-server",
                "localhost:9092",
                "--entity-type",
                "brokers",
                "--entity-name",
                "0",
                "--all",
            ],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="Kafka config check failed")

        lines = p.stdout.split("\n")[1:]
        runtime_config = {}
        for line in lines:
            if line.strip() != "":
                config = line.strip().split(" ")[0]
                [name, value] = config.split("=")
                if value == "true":
                    value = True
                elif value == "false":
                    value = False
                elif re.match(r"^-?\d+$", value) or re.match(
                    r"^-?\d+\.\d+$", value
                ):
                    value = float(value)
                runtime_config[name] = value

        for n in kafka_config:
            if not n in runtime_config:
                return OracleResult(
                    message=f"Kafka config check failed due to missing keys {n}"
                )
            elif runtime_config[n] != kafka_config[n]:
                return OracleResult(
                    message=f"Kafka config check failed due to inconsistent value of the {n}"
                )

        return None

    def __check_availability(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Kafka writer availability rate parsing its logs"""
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
            name="kafka-writer",
            namespace=self.oracle_handle.namespace,
            container="kafka-writer",
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
                        message="Kafka writer availability rate is below 90%"
                    )
            else:
                logger.warning(
                    "Unable to parse Kafka writer log line: %s", line
                )
                continue

        if min_avail_rate is not None:
            logger.info(
                "Kafka writer lowest availability rate: %f", min_avail_rate
            )
        else:
            logger.error("Kafka writer availability rate not found")

        return None

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Kafka config and availability"""
        if result := self.__check_config(generation, snapshot, prev_snapshot):
            return result
        if result := self.__check_availability(
            generation, snapshot, prev_snapshot
        ):
            return result
        return None


def deploy_writer(handle: OracleHandle):
    """Deploy the Writer Pod for Oracle"""

    handle.kubectl_client.kubectl(
        [
            "apply",
            "-f",
            "data/strimzi-kafka-operator/v0-45-0/writer_pod.yaml",
            "-n",
            handle.namespace,
        ]
    )


CUSTOM_CHECKER: type[CheckerInterface] = KafkaConfigChecker
ON_INIT: Callable = deploy_writer
