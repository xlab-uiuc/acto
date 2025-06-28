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


class MinIOConfigChecker(CheckerInterface):
    """Custom oracle for checking MinIO config"""

    name = "minio-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra config"""
        logger = get_thread_logger()
        logger.info("Checking MinIO config")
        if (
            "storage-configuration" in snapshot.system_state["secret"]
        ):
            minio_config = snapshot.system_state["secret"]["storage-configuration"]["data"]["config.env"].strip().split("\n")
        else:
            return OracleResult(message=f"Missing the Secret that contains the configuration")
        
        pod_name = "test-cluster-pool-0-0"
        namespace = "minio-operator"
        # set alias
        p = self.oracle_handle.kubectl_client.exec(
            pod_name,
            namespace,
            [
                "mc",
                "alias",
                "set",
                "myminio",
                "https://minio.minio-operator.svc.cluster.local",
                "minio",
                "minio123"
            ],
            capture_output=True,
            text=True,
        )
        # get config
        p = self.oracle_handle.kubectl_client.exec(
            pod_name,
            namespace,
            [
                "mc",
                "admin",
                "config",
                "export",
                "myminio"
            ],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            return OracleResult(message="MinIO config check failed")

        lines = p.stdout.split("\n")
        runtime_config = [config[2:] for config in lines if re.match(r"^\# MINIO_.*$", config)]

        missing_config = []

        for env_config in minio_config:
            if "MINIO_ROOT" not in env_config and "MINIO_BROWSER" not in env_config and env_config not in runtime_config:
                missing_config.append(env_config)
        
        if missing_config:
            return OracleResult(message="The following configurations " + str(missing_config) + " are missing.")

        return None


CUSTOM_CHECKER: type[CheckerInterface] = MinIOConfigChecker