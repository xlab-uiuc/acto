import glob
import json
import os
from enum import Enum
from typing import Dict, List

import yaml

from acto.checker.impl.health import HealthChecker
from acto.common import PassResult
from acto.snapshot import Snapshot


def construct_snapshot(trial_dir: str, generation: int):
    """Constructs a snapshot from the trial directory and generation"""
    mutated_path = f"{trial_dir}/mutated-{generation:03d}.yaml"
    operator_log_path = f"{trial_dir}/operator-{generation:03d}.log"
    system_state_path = f"{trial_dir}/system-state-{generation:03d}.json"
    cli_output_path = f"{trial_dir}/cli-output-{generation:03d}.log"

    with open(mutated_path, "r") as mutated_file, open(
        operator_log_path, "r"
    ) as operator_log_file, open(
        system_state_path, "r"
    ) as system_state_file, open(
        cli_output_path, "r"
    ) as cli_output_file:
        mutated = yaml.load(mutated_file, Loader=yaml.FullLoader)
        operator_log = operator_log_file.read().splitlines()
        system_state = json.load(system_state_file)
        cli_output = json.load(cli_output_file)

        return Snapshot(mutated, cli_output, system_state, operator_log)


class BugCateogry(str, Enum):
    UNDESIRED_STATE = "undesired_state"
    SYSTEM_ERROR = "system_error"
    OPERATOR_ERROR = "operator_error"
    RECOVERY_FAILURE = "recovery_failure"

    def __str__(self) -> str:
        return self.value


class BugConsequence(str, Enum):
    SYSTEM_FAILURE = "System failure"
    RELIABILITY_ISSUE = "Reliability issue"
    SECURITY_ISSUE = "Security issue"
    RESOURCE_ISSUE = "Resource issue"
    OPERATION_OUTAGE = "Operation outage"
    MISCONFIGURATION = "Misconfiguration"


class BugConfig:
    def __init__(
        self,
        category: BugCateogry,
        dir: str,
        diffdir: str = None,
        declaration: bool = False,
        difftest: bool = False,
        runtime_error: bool = False,
        recovery: bool = False,
        consequences: List[BugConsequence] = None,
    ) -> None:
        self._category = category
        self._dir = dir
        self._diffdir = diffdir
        self._declaration = declaration
        self._difftest = difftest
        self._runtime_error = runtime_error
        self._recovery = recovery

        if consequences is None:
            self._consequences = []
        else:
            self._consequences = consequences

    @property
    def category(self) -> BugCateogry:
        return self._category

    @property
    def dir(self) -> str:
        """The relative directory containing the inputs for reproducing this bug"""
        return self._dir

    @property
    def diffdir(self) -> str:
        """The relative directory containing the inputs for reproducing this bug through difftest

        Only specified when "dir" cannot does not trigger the difftest alarm for this bug
        """
        return self._diffdir

    @property
    def declaration(self) -> bool:
        """If the bug is found by the system consistency oracle"""
        return self._declaration

    @property
    def difftest(self) -> bool:
        """If the bug is found by the differential oracle"""
        return self._difftest

    @property
    def runtime_error(self) -> bool:
        """If the bug if found by runtime error"""
        return self._runtime_error

    @property
    def recovery(self) -> bool:
        """If the bug if found by the recovery step"""
        return self._recovery

    @property
    def consequences(self) -> List[str]:
        """The list of consequence categories this bug cause"""
        return self._consequences


class OperatorPrettyName(str, Enum):
    CASS_OPERATOR = "CassOp"
    COCKROACH_OPERATOR = "CockroachOp"
    KNATIVE_OPERATOR = "KnativeOp"
    OCK_REDIS_OPERATOR = "OCK-RedisOp"
    OFC_MONGODB_OPERATOR = "OFC-MongoDBOp"
    PCN_MONGODB_OPERATOR = "PCN-MongoDBOp"
    RABBITMQ_OPERATOR = "RabbitMQOp"
    SAH_REDIS_OPERATOR = "SAH-RedisOp"
    TIDB_OPERATOR = "TiDBOp"
    XTRADB_OPERATOR = "XtraDBOp"
    ZOOKEEPER_OPERATOR = "ZookeeperOp"


# Mapping from operator name to pretty name
operator_pretty_name_mapping: Dict[str, OperatorPrettyName] = {
    "cass-operator": OperatorPrettyName.CASS_OPERATOR,
    "cockroach-operator": OperatorPrettyName.COCKROACH_OPERATOR,
    "knative-operator": OperatorPrettyName.KNATIVE_OPERATOR,
    "redis-ot-container-kit-operator": OperatorPrettyName.OCK_REDIS_OPERATOR,
    "mongodb-community-operator": OperatorPrettyName.OFC_MONGODB_OPERATOR,
    "percona-server-mongodb-operator": OperatorPrettyName.PCN_MONGODB_OPERATOR,
    "rabbitmq-operator": OperatorPrettyName.RABBITMQ_OPERATOR,
    "redis-operator": OperatorPrettyName.SAH_REDIS_OPERATOR,
    "tidb-operator": OperatorPrettyName.TIDB_OPERATOR,
    "percona-xtradb-cluster-operator": OperatorPrettyName.XTRADB_OPERATOR,
    "zookeeper-operator": OperatorPrettyName.ZOOKEEPER_OPERATOR,
}

all_bugs: Dict[str, Dict[str, BugConfig]] = {
    "cass-operator": {
        "cassop-315": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="cassop-315/inputs",
            recovery=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "cassop-330": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="cassop-330/trial-demo",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "cassop-334": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="cassop-334",
            recovery=True,
            consequences=[
                BugConsequence.RELIABILITY_ISSUE,
                BugConsequence.OPERATION_OUTAGE,
            ],
        ),
        "cassop-471": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="cassop-471",
            declaration=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
    },
    "cockroach-operator": {
        "crdbop-918": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="crdbop-918",
            runtime_error=True,
            consequences=[
                BugConsequence.OPERATION_OUTAGE,
                BugConsequence.MISCONFIGURATION,
            ],
        ),
        "crdbop-919": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="crdbop-919",
            difftest=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "crdbop-920": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="crdbop-920/inputs",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.SECURITY_ISSUE],
        ),
        "crdbop-927": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="crdbop-927",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "crdbop-953": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="crdbop-953",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
    },
    "knative-operator-serving": {
        "knop-1137": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="knop-1137",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "knop-1157": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="knop-1157",
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
    },
    "knative-operator-eventing": {
        "knop-1158": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="knop-1158",
            runtime_error=True,
            consequences=[
                BugConsequence.SYSTEM_FAILURE,
                BugConsequence.RELIABILITY_ISSUE,
            ],
        ),
    },
    "mongodb-community-operator": {
        "mgopone-1024": BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir="mgopone-1024",
            difftest=True,
            runtime_error=True,
            consequences=[BugConsequence.SYSTEM_FAILURE],
        ),
        "mgopone-1054": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="mgopone-1054",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "mgopone-1055": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="mgopone-1055",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "mgopone-1072": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="mgopone-1072",
            recovery=True,
            consequences=[
                BugConsequence.SYSTEM_FAILURE,
                BugConsequence.RELIABILITY_ISSUE,
            ],
        ),
        "mgopone-1074": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="mgopone-1074",
            difftest=True,
            consequences=[BugConsequence.SECURITY_ISSUE],
        ),
        "mgopone-1245": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="mgopone-1245",
            recovery=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "mgopone-1251": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="mgopone-1251",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
        "mgopone-1252": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="mgopone-1252",
            difftest=True,
            consequences=[
                BugConsequence.RELIABILITY_ISSUE,
                BugConsequence.OPERATION_OUTAGE,
            ],
        ),
    },
    "percona-server-mongodb-operator": {
        "mgoptwo-696": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="mgoptwo-696",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "mgoptwo-738": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="mgoptwo-738",
            declaration=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "mgoptwo-742": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="mgoptwo-742",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "mgoptwo-895": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="mgoptwo-895",
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "mgoptwo-897": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="mgoptwo-897",
            recovery=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
    },
    "percona-xtradb-cluster-operator": {
        "xtop-1060": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="xtop-1060",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "xtop-1061": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="xtop-1061",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "xtop-1067": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="xtop-1067",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "xtop-1068": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="xtop-1068",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "xtop-1069": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="xtop-1069",
            declaration=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "xtop-1155": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="xtop-1155",
            recovery=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
    },
    "rabbitmq-operator": {
        "rbop-928": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rbop-928",
            declaration=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
        "rbop-968": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rbop-968",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "rbop-992": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rbop-992",
            difftest=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
    },
    "redis-operator": {
        "rdopone-400": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rdopone-400",
            difftest=True,
            declaration=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "rdopone-407": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rdopone-407",
            declaration=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "rdopone-552": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="rdopone-552",
            recovery=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
    },
    "redis-ot-container-kit-operator": {
        "rdoptwo-280": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rdoptwo-280",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "rdoptwo-283": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="rdoptwo-283",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "rdoptwo-286": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="rdoptwo-286",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "rdoptwo-287": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rdoptwo-287",
            declaration=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
        "rdoptwo-290": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rdoptwo-290",
            declaration=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "rdoptwo-292": BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir="rdoptwo-291",
            runtime_error=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
        "rdoptwo-297": BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir="rdoptwo-297",
            runtime_error=True,
            consequences=[
                BugConsequence.SYSTEM_FAILURE,
                BugConsequence.RELIABILITY_ISSUE,
            ],
        ),
        "rdoptwo-474": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="rdoptwo-474",
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "rdoptwo-480": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="rdoptwo-480",
            recovery=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
    },
    "tidb-operator": {
        "tiop-4613": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="tiop-4613/normal",
            diffdir="tiop-4613/diff",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "tiop-4684": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="tiop-4684",
            declaration=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
        "tiop-4945": BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir="tiop-4945",
            runtime_error=True,
            consequences=[
                BugConsequence.SYSTEM_FAILURE,
                BugConsequence.RELIABILITY_ISSUE,
            ],
        ),
        "tiop-4946": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="tiop-4946",
            recovery=True,
            consequences=[
                BugConsequence.OPERATION_OUTAGE,
                BugConsequence.RELIABILITY_ISSUE,
            ],
        ),
    },
    "zookeeper-operator": {
        "zkop-454": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="zkop-454",
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "zkop-474": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="zkop-474",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.MISCONFIGURATION],
        ),
        "zkop-513": BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir="zkop-513",
            runtime_error=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
        "zkop-540": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="zkop-540",
            declaration=True,
            difftest=True,
            consequences=[BugConsequence.RESOURCE_ISSUE],
        ),
        "zkop-541": BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir="zkop-541",
            difftest=True,
            consequences=[BugConsequence.RELIABILITY_ISSUE],
        ),
        "zkop-547": BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir="zkop-547",
            recovery=True,
            consequences=[BugConsequence.OPERATION_OUTAGE],
        ),
    },
}


def check_postdiff_runtime_error(workdir_path: str) -> bool:
    """Checks if there is runtime error manifested in the postdiff run"""
    post_diff_test_dir = os.path.join(workdir_path, "post_diff_test")
    compare_results = glob.glob(
        os.path.join(post_diff_test_dir, "compare-results-*.json")
    )
    if len(compare_results) == 0:
        return False
    else:
        for compare_result in compare_results:
            with open(compare_result) as f:
                result = json.load(f)[0]
                to_state = result["to"]
                snapshot = Snapshot({})
                snapshot.system_state = to_state
                health_result = HealthChecker().check(0, snapshot, {})
                if not isinstance(health_result, PassResult):
                    return True

    return False
