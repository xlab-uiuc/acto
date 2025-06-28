import base64
import datetime
import json
import re
from typing import Callable, Optional

import kubernetes
import yaml

# pylint: disable=import-error
from acto.checker.checker import CheckerInterface
from acto.checker.impl.state_compare import CustomCompareMethods
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger

# pylint: enable=import-error


class MongoDBConfigChecker(CheckerInterface):
    """Custom oracle for checking MongoDB config"""

    name = "mongodb-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle
        self._previous_ts: Optional[datetime.datetime] = None

    def __check_config(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the MongoDB config"""
        _, _ = generation, prev_snapshot

        if (
            "replsets" in snapshot.input_cr["spec"]
            and len(snapshot.input_cr["spec"]["replsets"]) > 0
            and "configuration" in snapshot.input_cr["spec"]["replsets"][0]
        ):
            mongo_yaml = yaml.load(
                snapshot.input_cr["spec"]["replsets"][0]["configuration"],
                Loader=yaml.FullLoader,
            )
        else:
            return None

        sts_list = self.oracle_handle.get_stateful_sets()
        rs_sts = None
        for sts in sts_list:
            if sts.metadata.labels["app.kubernetes.io/component"] == "mongod":
                rs_sts = sts
        pod_list = self.oracle_handle.get_pods_in_stateful_set(rs_sts)

        core_v1 = kubernetes.client.CoreV1Api(self.oracle_handle.k8s_client)

        secret = core_v1.read_namespaced_secret(
            "my-cluster-name-secrets", self.oracle_handle.namespace
        ).data

        username = base64.b64decode(
            secret["MONGODB_DATABASE_ADMIN_USER"]
        ).decode("utf-8")
        password = base64.b64decode(
            secret["MONGODB_DATABASE_ADMIN_PASSWORD"]
        ).decode("utf-8")

        pod = pod_list[0]
        p = self.oracle_handle.kubectl_client.exec(
            pod.metadata.name,
            pod.metadata.namespace,
            [
                "mongosh",
                "-u",
                username,
                "-p",
                password,
                "--eval",
                "db.adminCommand({getCmdLineOpts: 1})",
            ],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="MongoDB config check failed")

        lines = p.stdout.split("\n")
        mark = 0
        for i in range(len(lines)):
            if re.match("{", lines[i]):
                mark = i
                break
        config_data = [x + "\n" for x in lines[i:]]

        mark = 0
        for i in range(len(config_data)):
            config_data[i] = re.sub(r"(\w+):", r'"\g<1>":', config_data[i])
            config_data[i] = re.sub(r"'(.+)'", r'"\g<1>"', config_data[i])
            if '"ok":' in config_data[i]:
                mark = i
                break
        config_data[mark - 1] = re.sub(
            r"(\w*)},", r"\g<1>}", config_data[mark - 1]
        )
        config_data = json.loads("".join(config_data[:mark] + ["}"]))["parsed"]

        compare_methods = CustomCompareMethods()
        if not compare_methods.equals(mongo_yaml, config_data):
            return OracleResult(
                message="MongoDB config check failed due to missing keys or wrong values"
            )

        return None

    def __check_availability(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the MongoDB writer availability rate parsing its logs"""
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
            name="mongodb-writer",
            namespace=self.oracle_handle.namespace,
            container="mongodb-writer",
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
                        message="MongoDB writer availability rate is below 90%"
                    )
            else:
                logger.warning(
                    "Unable to parse MongoDB writer log line: %s", line
                )
                continue

        if min_avail_rate is not None:
            logger.info(
                "MongoDB writer lowest availability rate: %f", min_avail_rate
            )
        else:
            logger.error("MongoDB writer availability rate not found")

        return None

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the MongoDB config and availability"""
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
            "data/percona-server-mongodb-operator/v1-16-0/writer_pod.yaml",
            "-n",
            handle.namespace,
        ]
    )


CUSTOM_CHECKER: type[CheckerInterface] = MongoDBConfigChecker

ON_INIT: Callable = deploy_writer
