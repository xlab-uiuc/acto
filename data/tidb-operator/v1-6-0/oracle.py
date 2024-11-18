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

        if (
            "tidb" in snapshot.input_cr["spec"]
            and "config" in snapshot.input_cr["spec"]["tidb"]["config"]
        ):
            tidb_spec_config = snapshot.input_cr["spec"]["tidb"]["config"]
        else:
            return None
        
        prefix = ""
        tidb_spec_config = tidb_spec_config.split("\n")
        tidb_config = {}
        for i in range(len(tidb_config)):
            if re.match("[(\w+)]", tidb_config[i]):
                prefix = re.match("[(\w+)]", tidb_config[i]).group(1)
            elif re.match("\w+=", tidb_config[i]):
                tidb_config[prefix + "." +re.match("\w+=", tidb_config[i]).group(1)] = re.match("\w+=", tidb_config[i]).group(2)
            else:
                logger.error("Failed to parse line: %s", tidb_config[i])

        p = self.oracle_handle.kubectl_client.exec(
            "mysql-pod",
            "acto-namespace",
            [
                "mysql",
                "--comments",
                "-h",
                "test-cluster-tidb"
                "-P",
                4000,
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
            all_node_config[compoents[1]][compoents[2]] = compoents[3]
        
        first_node = all_node_config.keys()[0]
        first_tidb_config = all_node_config[first_node]
        for node in all_node_config:
            if all_node_config[node] != first_tidb_config:
                return OracleResult(message=f"TiDB config check failed due to inconsistent config between nodes {first_node} and {node}")

        compare_methods = CustomCompareMethods()
        if not compare_methods.equals(tidb_config, first_tidb_config):
            return OracleResult(message="TiDB config check failed due to missing keys or wrong values")

        return None
    
def deploy_mysql(handle: OracleHandle):
    handle.kubectl_client.kubectl([
        'apply', '-f', '- <<EOF\napiVersion: v1\nkind: Pod\nmetadata:\n  name: busybox-sleep\nspec:\n  containers:\n  - name: busybox\n    image: busybox:1.28\n    args:\n    - sleep\n    - "1000000"\n---\napiVersion: v1\nkind: Pod\nmetadata:\n  name: busybox-sleep-less\nspec:\n  containers:\n  - name: busybox\n    image: busybox:1.28\n    args:\n    - sleep\n    - "1000"\nEOF', '-l', 'acto/tag=custom-oracle', '-n',
        handle.namespace
    ])


CUSTOM_CHECKER: list[type] = [TiDBConfigChecker]
ON_INIT: list[callable] = [deploy_mysql]