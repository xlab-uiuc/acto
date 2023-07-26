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
    

class BugConfig:

    def __init__(self, category: BugCateogry, dir: str, difftest: bool = False) -> None:
        self.category = category
        self.dir = dir
        self.difftest = difftest

    
all_bugs = {
    'cass-operator': {
        'cassop-315': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE, 
            dir='test/cassop-315/trial-04-0000'
        ),
        'cassop-330': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/cassop-330/trial-demo',
        ),
        'cassop-334': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/cassop-334',
        ),
        'cassop-471': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/cassop-471',
        ),
    },
    'cockroach-operator': {
        'crdbop-918': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/crdbop-918',
        ),
        'crdbop-919': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/crdbop-919',
            difftest=True,
        ),
        'crdbop-920': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/crdbop-920',
        ),
        'crdbop-927': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/crdbop-927',
        ),
        'crdbop-953': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/crdbop-953',
        ),
    },
    'knative-operator-serving': {
        'knop-1137': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/knop-1137',
        ),
        'knop-1157': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/knop-1157',
            difftest=True,
        ),
    },
    'knative-operator-eventing': {
        'knop-1158': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/knop-1158',
        ),
    },
    'mongodb-community-operator': {
        'mgopone-1024': BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir='test/mgopone-1024',
            difftest=True,
        ),
        'mgopone-1054': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/mgopone-1054',
        ),
        'mgopone-1055': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/mgopone-1055',
        ),
        'mgopone-1072': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/mgopone-1072',
        ),
        'mgopone-1074': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/mgopone-1074',
            difftest=True,
        ),
        'mgopone-1245': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/mgopone-1245',
        ),
        'mgopone-1251': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/mgopone-1251',
            difftest=True,
        ),
        'mgopone-1252': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/mgopone-1252',
            difftest=True,
        ),
    },
    'percona-server-mongodb-operator': {
        'mgoptwo-696': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/mgoptwo-696',
        ),
        'mgoptwo-738': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/mgoptwo-738',
        ),
        'mgoptwo-742': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/mgoptwo-742',
        ),
        'mgoptwo-895': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/mgoptwo-895',
            difftest=True,
        ),
        'mgoptwo-897': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/mgoptwo-897',
        ),
    },
    'percona-xtradb-cluster-operator': {
        'xtop-1060': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/xtop-1060',
        ),
        'xtop-1061': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/xtop-1061',
        ),
        'xtop-1067': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/xtop-1067',
        ),
        'xtop-1068': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/xtop-1068',
        ),
        'xtop-1069': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/xtop-1069',
        ),
        'xtop-1155': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/xtop-1155',
        ),
    },
    'rabbitmq-operator': {
        'rbop-928': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rbop-928',
        ),
        'rbop-968': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rbop-968',
        ),
        'rbop-992': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rbop-992',
            difftest=True,
        ),
    },
    'redis-operator': {
        'rdopone-400': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rdopone-400',
        ),
        'rdopone-407': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rdopone-407',
        ),
        'rdopone-552': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/rdopone-552',
        ),
    },
    'redis-ot-container-kit-operator': {
        'rdoptwo-280': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rdoptwo-280',
        ),
        'rdoptwo-283': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/rdoptwo-283',
        ),
        'rdoptwo-286': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/rdoptwo-286',
        ),
        'rdoptwo-287': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rdoptwo-287',
        ),
        'rdoptwo-290': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rdoptwo-290',
        ),
        'rdoptwo-292': BugConfig(
            category=BugCateogry.OPERATOR_ERROR,
            dir='test/rdoptwo-291',
        ),
        'rdoptwo-297': BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir='test/rdoptwo-297',
        ),
        'rdoptwo-474': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/rdoptwo-474',
            difftest=True,
        ),
        'rdoptwo-480': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/rdoptwo-480',
        ),
    },
    'tidb-operator': {
        'tiop-4613': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/tiop-4613',
        ),
        'tiop-4684': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/tiop-4684',
        ),
        'tiop-4945': BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir='test/tiop-4945',
        ),
        'tiop-4946': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/tiop-4946',
        ),
    },
    'zookeeper-operator': {
        'zkop-454': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/zkop-454',
            difftest=True,
        ),
        'zkop-474': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/zkop-474',
        ),
        'zkop-513': BugConfig(
            category=BugCateogry.SYSTEM_ERROR,
            dir='test/zkop-513',
        ),
        'zkop-540': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/zkop-540',
        ),
        'zkop-541': BugConfig(
            category=BugCateogry.UNDESIRED_STATE,
            dir='test/zkop-541',
            difftest=True,
        ),
        'zkop-547': BugConfig(
            category=BugCateogry.RECOVERY_FAILURE,
            dir='test/zkop-547',
        ),
    }
}
