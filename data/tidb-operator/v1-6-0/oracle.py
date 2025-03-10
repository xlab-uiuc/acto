import datetime
import re
from typing import Callable, Optional

import kubernetes
import tomlkit

# pylint: disable=import-error
from acto.checker.checker import CheckerInterface
from acto.checker.impl.state_compare import CustomCompareMethods
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger

# pylint: enable=import-error


class TiDBConfigChecker(CheckerInterface):
    """Custom oracle for checking TiDB config"""

    name = "tidb-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle
        self._previous_ts: Optional[datetime.datetime] = None

    def __check_config(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the TiDB config"""
        _, _, _ = generation, snapshot, prev_snapshot

        logger = get_thread_logger()
        logger.info("Checking TiDB config")
        if (
            "tidb" in snapshot.input_cr["spec"]
            and "config" in snapshot.input_cr["spec"]["tidb"]
        ):
            tidb_spec_config = snapshot.input_cr["spec"]["tidb"]["config"]
        else:
            return None

        tidb_config = tomlkit.loads(tidb_spec_config)

        p = self.oracle_handle.kubectl_client.exec(
            "mysql-pod",
            "acto-namespace",
            [
                "mysql",
                "--comments",
                "-h",
                "test-cluster-tidb",
                "-P",
                "4000",
                "-u",
                "root",
                "--execute",
                "SHOW CONFIG WHERE type = 'tidb';",
            ],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="TiDB config check failed")

        lines = p.stdout.split("\n")[1:]
        all_node_config: dict[str, dict] = {}
        for line in lines:
            compoents = line.split("\t")
            if len(compoents) < 4:
                continue
            if compoents[1] not in all_node_config:
                all_node_config[compoents[1]] = {}
            result = all_node_config[compoents[1]]
            keys = compoents[2].split(".")
            for key in keys[:-1]:
                if key not in result:
                    result[key] = {}
                result = result[key]
            if compoents[3] == "true" or compoents[3] == "false":
                result[keys[-1]] = bool(compoents[3])
            elif re.match(r"^\d+$", compoents[3]) or re.match(
                r"^\d+\.\d+$", compoents[3]
            ):
                result[keys[-1]] = float(compoents[3])
            else:
                result[keys[-1]] = compoents[3]

        compare_methods = CustomCompareMethods()
        for node, value in all_node_config.items():
            if not compare_methods.equals(tidb_config, value):
                return OracleResult(
                    message="TiDB config check failed due to "
                    f"missing keys or wrong values in node {node}"
                )

        return None

    def __check_availability(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the TiDB writer availability rate parsing its logs"""
        _, _, _ = generation, snapshot, prev_snapshot

        v1 = kubernetes.client.CoreV1Api(self.oracle_handle.k8s_client)
        now = datetime.datetime.now()
        since_seconds: Optional[int] = (
            None
            if self._previous_ts is None
            else int((now - self._previous_ts).total_seconds())
        )
        logs = v1.read_namespaced_pod_log(
            name="writer",
            namespace="acto-namespace",
            container="writer",
            since_seconds=since_seconds,
        ).split("\n")
        self._previous_ts = now

        min_avail_rate: Optional[float] = None
        for line in logs:
            match = re.search(r"TS: \[(.*?)\].*?Success Rate: \[(.*?)\]", line)
            if match:
                _ = match.group(1)
                success_rate = match.group(2)

                if float(success_rate) < 0.9:
                    return OracleResult(
                        message="TiDB writer availability rate is below 90%"
                    )
            else:
                continue

        logger = get_thread_logger()
        if min_avail_rate is not None:
            logger.info(
                "TiDB writer lowest availability rate: %f", min_avail_rate
            )
        else:
            logger.error("TiDB writer availability rate not found")

        return None

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the TiDB config and availability"""
        if result := self.__check_config(generation, snapshot, prev_snapshot):
            return result
        if result := self.__check_availability(
            generation, snapshot, prev_snapshot
        ):
            return result
        return None


def deploy_mysql(handle: OracleHandle):
    """Deploy the MySQL Pod for Oracle"""
    handle.kubectl_client.kubectl(
        [
            "apply",
            "-f",
            "data/tidb-operator/v1-6-0/mysql_pod.yaml",
            "-n",
            handle.namespace,
        ]
    )

    handle.kubectl_client.kubectl(
        [
            "apply",
            "-f",
            "data/tidb-operator/v1-6-0/writer_pod.yaml",
            "-n",
            handle.namespace,
        ]
    )


CUSTOM_CHECKER: type[CheckerInterface] = TiDBConfigChecker
ON_INIT: Callable = deploy_mysql
