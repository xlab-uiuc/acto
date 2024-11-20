import base64
from typing import Optional

import kubernetes

from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger
from acto.checker.impl.state_compare import CustomCompareMethods
import configparser
from acto.k8s_util.k8sutil import canonicalize_quantity

def decode(value: str) -> dict:
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
    """Custom oracle for checking TiDB config"""

    name = "tidb-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra config"""
        logger = get_thread_logger()

        if (
            "myCnf" in snapshot.input_cr["spec"]
        ):
            mairadb_spec_config = snapshot.input_cr["spec"]["myCnf"]
        else:
            return None
        
        mariadb_spec_config = decode(mairadb_spec_config)["mariadb"]

        for key, value in mariadb_spec_config.items():
            mariadb_spec_config[key] = canonicalize_quantity(value)
            print(canonicalize_quantity(value))
        
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
                "mariadb",
                "-u", 
                username, 
                f"-p{password}", 
                "-e", 
                "SHOW VARIABLES;"
            ],
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
            else:
                mariadb_config[compoents[0]] = canonicalize_quantity(compoents[1])

        compare_methods = CustomCompareMethods()
        if not compare_methods.equals(mariadb_spec_config, mariadb_config):
            return OracleResult(message=f"MariaDB config check failed due to missing keys or wrong values.")

        return None


CUSTOM_CHECKER: type[CheckerInterface] = MariaDBConfigChecker