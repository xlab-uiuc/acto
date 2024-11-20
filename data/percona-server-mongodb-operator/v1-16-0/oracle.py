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


class MongoDBConfigChecker(CheckerInterface):
    """Custom oracle for checking Cassandra config"""

    name = "mongodb-config-checker"

    def __init__(self, oracle_handle: OracleHandle, **kwargs):
        super().__init__(**kwargs)
        self.oracle_handle = oracle_handle

    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the Cassandra config"""
        logger = get_thread_logger()

        if (
            "replsets" in snapshot.input_cr["spec"]
            and len(snapshot.input_cr["spec"]["replsets"]) > 0
            and "configuration" in snapshot.input_cr["spec"]["replsets"][0]
        ):
            mongo_yaml = yaml.load(snapshot.input_cr["spec"]["replsets"][0][
                "configuration"], Loader=yaml.FullLoader)
        else:
            return None

        sts_list = self.oracle_handle.get_stateful_sets()
        pod_list = self.oracle_handle.get_pods_in_stateful_set(sts_list[0])

        core_v1 = kubernetes.client.CoreV1Api(self.oracle_handle.k8s_client)

        secret = core_v1.read_namespaced_secret(
            "my-cluster-name-secrets", self.oracle_handle.namespace
        ).data

        username = base64.b64decode(secret["MONGODB_DATABASE_ADMIN_USER"]).decode("utf-8")
        password = base64.b64decode(secret["MONGODB_DATABASE_ADMIN_PASSWORD"]).decode("utf-8")

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
        lines = [x + "\n" for x in lines[17:]]

        mark = 0
        for i in range(len(lines)):
            lines[i] = re.sub("(\w+):", '"\g<1>":', lines[i])
            lines[i] = re.sub("'(.+)'", '"\g<1>"', lines[i])
            if '\"ok\":' in lines[i]:
                mark = i
                break
        lines[mark - 1] = re.sub("(\w*)},", '\g<1>}', lines[mark - 1])
        config_data = json.loads("".join(lines[:mark] + ["}"]))["parsed"]

        compare_methods = CustomCompareMethods()
        if not compare_methods.equals(mongo_yaml, config_data):
            return OracleResult(message="MongoDB config check failed due to missing keys or wrong values")

        return None


CUSTOM_CHECKER: type[CheckerInterface] = MongoDBConfigChecker
