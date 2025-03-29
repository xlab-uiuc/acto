import base64
import configparser
import datetime
import re
from typing import Callable, Optional

import kubernetes

# pylint: disable=import-error
from acto.checker.checker import CheckerInterface
from acto.checker.impl.state_compare import CustomCompareMethods
from acto.k8s_util.k8sutil import canonicalize_quantity
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger

# pylint: enable=import-error


def decode(value: str) -> dict:
    """Decode the config string to dictionary"""
    config = configparser.ConfigParser()
    config.read_string(value)

    sections_dict = {}

    # get all defaults
    defaults = config.defaults()
    temp_dict = {}
    for key in defaults.keys():
        temp_dict[key] = defaults[key]

    sections_dict["default"] = temp_dict

    # get sections and iterate over each
    sections = config.sections()

    for section in sections:
        options = config.options(section)
        temp_dict = {}
        for option in options:
            temp_dict[option] = config.get(section, option)

        sections_dict[section] = temp_dict

    return sections_dict


class MariaDBConfigChecker(CheckerInterface):
    """Custom oracle for checking MariaDB config"""

    name = "mariadb-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle
        self._previous_ts: Optional[datetime.datetime] = None

    def __check_config(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the MariaDB config"""
        _, _ = generation, prev_snapshot

        if "myCnf" in snapshot.input_cr["spec"]:
            mairadb_spec_config = snapshot.input_cr["spec"]["myCnf"]
        else:
            return None

        mariadb_spec_config = decode(mairadb_spec_config)["mariadb"]

        for key, value in mariadb_spec_config.items():
            mariadb_spec_config[key] = (
                canonicalize_quantity(value)
                if not isinstance(canonicalize_quantity(value), str)
                else canonicalize_quantity(value).lower()
            )

        # Get the configuration from the cqlsh
        sts_list = self.oracle_handle.get_stateful_sets()
        pod_list = self.oracle_handle.get_pods_in_stateful_set(sts_list[0])

        core_v1 = kubernetes.client.CoreV1Api(self.oracle_handle.k8s_client)

        secret = core_v1.read_namespaced_secret(
            "mariadb", self.oracle_handle.namespace
        ).data

        password = base64.b64decode(secret["password"]).decode("utf-8")

        pod = pod_list[0]

        p = self.oracle_handle.kubectl_client.exec(
            pod.metadata.name,
            pod.metadata.namespace,
            ["mariadb", "-u", "root", f"-p{password}", "-e", "SHOW VARIABLES;"],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="MariaDB config check failed")

        lines = p.stdout.split("\n")[1:]
        mariadb_config = {}
        for line in lines:
            compoents = line.split("\t")
            if len(compoents) < 2:
                continue

            mariadb_config[compoents[0]] = (
                canonicalize_quantity(compoents[1])
                if not isinstance(canonicalize_quantity(compoents[1]), str)
                else canonicalize_quantity(compoents[1]).lower()
            )

        compare_methods = CustomCompareMethods()
        if not compare_methods.equals(mariadb_spec_config, mariadb_config):
            return OracleResult(
                message="MariaDB config check failed due to missing keys or wrong values."
            )

        return None

    def __check_availability(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the MariaDB writer availability rate parsing its logs"""
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
            name="mariadb-writer",
            namespace=self.oracle_handle.namespace,
            container="mariadb-writer",
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
                        message="MariaDB writer availability rate is below 90%"
                    )
            else:
                logger.warning(
                    "Unable to parse MariaDB writer log line: %s", line
                )
                continue

        if min_avail_rate is not None:
            logger.info(
                "MariaDB writer lowest availability rate: %f", min_avail_rate
            )
        else:
            logger.error("MariaDB writer availability rate not found")

        return None

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the MariaDB config and availability"""
        if result := self.__check_config(generation, snapshot, prev_snapshot):
            return result
        if result := self.__check_availability(
            generation, snapshot, prev_snapshot
        ):
            return result
        return None


CUSTOM_CHECKER: type[CheckerInterface] = MariaDBConfigChecker


def deploy_writer(handle: OracleHandle):
    """Deploy the Writer Pod for Oracle"""

    handle.kubectl_client.kubectl(
        [
            "apply",
            "-f",
            "data/mariadb-operator/v0-30-0/writer_pod.yaml",
            "-n",
            handle.namespace,
        ]
    )


ON_INIT: Callable = deploy_writer
