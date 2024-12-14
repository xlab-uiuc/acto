import base64
from typing import Optional

import kubernetes

from acto.checker.checker import CheckerInterface
from acto.oracle_handle import OracleHandle
from acto.result import OracleResult
from acto.snapshot import Snapshot
from acto.utils.thread_logger import get_thread_logger
from acto.checker.impl.state_compare import CustomCompareMethods
import json
import yaml
import re
import tomlkit


class TiDBConfigChecker(CheckerInterface):
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
                "test-cluster-tidb"
                "-P",
                "4000",
                "-u",
                "root",
                "--execute",
                "SHOW CONFIG WHERE type = 'tidb';"
            ],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="TiDB config check failed")

        lines = p.stdout.split("\n")[1:]
        all_node_config = {}
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
            elif re.match(r"^\d+$", compoents[3]) or re.match(r"^\d+\.\d+$", compoents[3]):
                result[keys[-1]] = float(compoents[3])
            else:
                result[keys[-1]] = compoents[3]

        compare_methods = CustomCompareMethods()
        for node in all_node_config:
            if not compare_methods.equals(tidb_config, all_node_config[node]):
                return OracleResult(message=f"TiDB config check failed due to missing keys or wrong values in node {node}")

        return None
    
def deploy_mysql(handle: OracleHandle):
    handle.kubectl_client.kubectl([
        'apply', '-f', 'data/tidb-operator/v1-6-0/mysql_pod.yaml', '-n', handle.namespace
    ])


CUSTOM_CHECKER: type[CheckerInterface] = TiDBConfigChecker
ON_INIT: list[callable] = [deploy_mysql]