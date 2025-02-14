import base64
from typing import Optional

import kubernetes

from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger
from acto.checker.impl.state_compare import CustomCompareMethods
import yaml
import re


class KafkaConfigChecker(CheckerInterface):
    """Custom oracle for checking Kafka config"""

    name = "kafka-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra config"""
        logger = get_thread_logger()
        logger.info("Checking Kafka config")
        if (
            "kafka" in snapshot.input_cr["spec"]
            and "config" in snapshot.input_cr["spec"]["kafka"]
        ):
            kafka_config = yaml.load(snapshot.input_cr["spec"]["kafka"]["config"], Loader=yaml.FullLoader)
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
                "--all"
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
                elif re.match(r"^\d+$", value) or re.match(r"^\d+\.\d+$", value):
                    value = float(value)
                runtime_config[name] = value
        
        for n in kafka_config:
            if not n in runtime_config:
                return OracleResult(message=f"Kafka config check failed due to missing keys")
            elif runtime_config[n] != kafka_config[n]:
                return OracleResult(message=f"Kafka config check failed due to inconsistent value of the {name}")

        return None


CUSTOM_CHECKER: type[CheckerInterface] = KafkaConfigChecker