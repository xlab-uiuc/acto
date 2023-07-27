from enum import Enum
import json

import yaml

from acto.snapshot import Snapshot


def construct_snapshot(trial_dir: str, generation: int):
    mutated_path = f'{trial_dir}/mutated-{generation}.yaml'
    operator_log_path = f'{trial_dir}/operator-{generation}.log'
    system_state_path = "%s/system-state-%03d.json" % (trial_dir, generation)
    cli_output_path = f'{trial_dir}/cli-output-{generation}.log'

    with open(mutated_path, 'r') as mutated_file, \
            open(operator_log_path, 'r') as operator_log_file, \
            open(system_state_path, 'r') as system_state_file, \
            open(cli_output_path, 'r') as cli_output_file:

        mutated = yaml.load(mutated_file, Loader=yaml.FullLoader)
        operator_log = operator_log_file.read().splitlines()
        system_state = json.load(system_state_file)
        cli_output = json.load(cli_output_file)

        return Snapshot(mutated, cli_output, system_state, operator_log)


class BugCateogry(str, Enum):
    UNDESIRED_STATE = 'undesired_state'
    SYSTEM_ERROR = 'system_error'
    OPERATOR_ERROR = 'operator_error'
    RECOVERY_FAILURE = 'recovery_failure'

    def __str__(self) -> str:
        return self.value


class BugConsequence(str, Enum):
    SYSTEM_FAILURE = 'System failure'
    RELIABILITY_ISSUE = 'Reliability issue'
    SECURITY_ISSUE = 'Security issue'
    RESOURCE_ISSUE = 'Resource issue'
    OPERATION_OUTAGE = 'Operation outage'
    MISCONFIGURATION = 'Misconfiguration'


class BugConfig:

    def __init__(self,
                 category: BugCateogry,
                 dir: str,
                 diffdir: str = None,
                 declaration: bool = False,
                 difftest: bool = False,
                 runtime_error: bool = False,
                 recovery: bool = False) -> None:
        self.category = category
        self.dir = dir
        self.diffdir = diffdir
        self.declaration = declaration
        self.difftest = difftest
        self.runtime_error = runtime_error
        self.recovery = recovery


all_bugs = {
    'cass-operator': {
        'cassop-315':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/cassop-315/inputs',
                recovery=True,
            ),
        'cassop-330':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/cassop-330/trial-demo',
                declaration=True,
                difftest=True,
            ),
        'cassop-334':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/cassop-334',
                recovery=True,
            ),
        'cassop-471':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/cassop-471',
                declaration=True,
            ),
    },
    'cockroach-operator': {
        'crdbop-918':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/crdbop-918',
                runtime_error=True,
            ),
        'crdbop-919':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/crdbop-919',
                difftest=True,
            ),
        'crdbop-920':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/crdbop-920/inputs',
                declaration=True,
                difftest=True,
            ),
        'crdbop-927':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/crdbop-927',
                declaration=True,
                difftest=True,
            ),
        'crdbop-953':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/crdbop-953',
                runtime_error=True,
            ),
    },
    'knative-operator-serving': {
        'knop-1137':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/knop-1137',
                runtime_error=True,
            ),
        'knop-1157':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/knop-1157',
                difftest=True,
            ),
    },
    'knative-operator-eventing': {
        'knop-1158':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/knop-1158',
                runtime_error=True,
            ),
    },
    'mongodb-community-operator': {
        'mgopone-1024':
            BugConfig(
                category=BugCateogry.SYSTEM_ERROR,
                dir='test/mgopone-1024',
                difftest=True,
                runtime_error=True,  # need to implement how to output this
            ),
        'mgopone-1054':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/mgopone-1054',
                runtime_error=True,
            ),
        'mgopone-1055':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/mgopone-1055',
                runtime_error=True,
            ),
        'mgopone-1072':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/mgopone-1072',
                recovery=True,
            ),
        'mgopone-1074':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/mgopone-1074',
                difftest=True,
            ),
        'mgopone-1245':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/mgopone-1245',
                recovery=True,
            ),
        'mgopone-1251':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/mgopone-1251',
                declaration=True,
                difftest=True,
            ),
        'mgopone-1252':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/mgopone-1252',
                difftest=True,
            ),
    },
    'percona-server-mongodb-operator': {
        'mgoptwo-696':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/mgoptwo-696',
                declaration=True,
                difftest=True,
            ),
        'mgoptwo-738':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/mgoptwo-738',
                declaration=True,
            ),
        'mgoptwo-742':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/mgoptwo-742',
                declaration=True,
                difftest=True,
            ),
        'mgoptwo-895':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/mgoptwo-895',
                difftest=True,
            ),
        'mgoptwo-897':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/mgoptwo-897',
                recovery=True,
            ),
    },
    'percona-xtradb-cluster-operator': {
        'xtop-1060':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/xtop-1060',
                runtime_error=True,
            ),
        'xtop-1061':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/xtop-1061',
                declaration=True,
                difftest=True,
            ),
        'xtop-1067':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/xtop-1067',
                declaration=True,
                difftest=True,
            ),
        'xtop-1068':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/xtop-1068',
                declaration=True,
                difftest=True,
            ),
        'xtop-1069':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/xtop-1069',
                declaration=True,
            ),
        'xtop-1155':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/xtop-1155',
                recovery=True,
            ),
    },
    'rabbitmq-operator': {
        'rbop-928':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rbop-928',
                declaration=True,
            ),
        'rbop-968':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rbop-968',
                declaration=True,
                difftest=True,
            ),
        'rbop-992':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rbop-992',
                difftest=True,
            ),
    },
    'redis-operator': {
        'rdopone-400':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rdopone-400',
                difftest=True,
                declaration=True,
            ),
        'rdopone-407':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rdopone-407',
                declaration=True,
            ),
        'rdopone-552':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/rdopone-552',
                recovery=True,
            ),
    },
    'redis-ot-container-kit-operator': {
        'rdoptwo-280':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rdoptwo-280',
                declaration=True,
                difftest=True,
            ),
        'rdoptwo-283':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/rdoptwo-283',
                runtime_error=True,
            ),
        'rdoptwo-286':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/rdoptwo-286',
                runtime_error=True,
            ),
        'rdoptwo-287':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rdoptwo-287',
                declaration=True,
            ),
        'rdoptwo-290':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rdoptwo-290',
                declaration=True,
            ),
        'rdoptwo-292':
            BugConfig(
                category=BugCateogry.OPERATOR_ERROR,
                dir='test/rdoptwo-291',
                runtime_error=True,
            ),
        'rdoptwo-297':
            BugConfig(
                category=BugCateogry.SYSTEM_ERROR,
                dir='test/rdoptwo-297',
                runtime_error=True,
            ),
        'rdoptwo-474':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/rdoptwo-474',
                difftest=True,
            ),
        'rdoptwo-480':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/rdoptwo-480',
                recovery=True,
            ),
    },
    'tidb-operator': {
        'tiop-4613':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/tiop-4613/normal',
                diffdir='test/tiop-4613/diff',
                declaration=True,
                difftest=True,
            ),
        'tiop-4684':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/tiop-4684',
                declaration=True,
            ),
        'tiop-4945':
            BugConfig(
                category=BugCateogry.SYSTEM_ERROR,
                dir='test/tiop-4945',
                runtime_error=True,
            ),
        'tiop-4946':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/tiop-4946',
                recovery=True,
            ),
    },
    'zookeeper-operator': {
        'zkop-454':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/zkop-454',
                difftest=True,
            ),
        'zkop-474':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/zkop-474',
                declaration=True,
                difftest=True,
            ),
        'zkop-513':
            BugConfig(
                category=BugCateogry.SYSTEM_ERROR,
                dir='test/zkop-513',
                runtime_error=True,
            ),
        'zkop-540':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/zkop-540',
                declaration=True,
                difftest=True,
            ),
        'zkop-541':
            BugConfig(
                category=BugCateogry.UNDESIRED_STATE,
                dir='test/zkop-541',
                difftest=True,
            ),
        'zkop-547':
            BugConfig(
                category=BugCateogry.RECOVERY_FAILURE,
                dir='test/zkop-547',
                recovery=True,
            ),
    }
}
