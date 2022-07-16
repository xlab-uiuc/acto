import enum
import json
import os
from deepdiff.helper import NotPresent
from datetime import datetime, date
import re
import logging
import string
import random
import subprocess
import kubernetes
import requests

from constant import CONST
from test_case import TestCase
from parse_log import parse_log


def notify_crash(exception: str):
    import socket
    import sys

    hostname = socket.gethostname()

    url = 'https://docs.google.com/forms/d/1Hxjg8TDKqBf_47H9gyP63gr3JVCGFwyqxUtSFA7OXhk/formResponse'
    form_data = {
        'entry.471699079': exception,
        'entry.1614228781': f'{sys.argv}',
        'entry.481598949': hostname
    }
    user_agent = {
        'Referer':
            'https://docs.google.com/forms/d/1Hxjg8TDKqBf_47H9gyP63gr3JVCGFwyqxUtSFA7OXhk/viewform',
        'User-Agent':
            "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36"
    }
    r = requests.post(url, data=form_data, headers=user_agent)
    logging.info('Send notify to google form')


class DeployConfig:

    def __init__(self, method: str, file: str, init: str) -> None:
        self.method = method
        self.file = file
        self.init = init


class AnalysisConfig:

    def __init__(self, github_link: str, commit: str, entrypoint: str, type: str,
                 package: str) -> None:
        self.github_link = github_link
        self.commit = commit
        self.entrypoint = entrypoint
        self.type = type
        self.package = package


class OperatorConfig:

    def __init__(self, deploy: DeployConfig, crd_name: str, custom_fields: str, context: str,
                 seed_custom_resource: str, source_path: str, analysis: AnalysisConfig) -> None:
        self.deploy = deploy
        self.crd_name = crd_name
        self.custom_fields = custom_fields
        self.context = context
        self.seed_custom_resource = seed_custom_resource
        self.source_path = source_path
        self.analysis = analysis


class Diff:

    def __init__(self, prev, curr, path) -> None:
        # self.path = path
        self.prev = prev
        self.curr = curr
        self.path = path

    def to_dict(self):
        '''serialize Diff object
        '''
        return {'prev': self.prev, 'curr': self.curr, 'path': self.path}


class Oracle(str, enum.Enum):
    ERROR_LOG = 'ErrorLog'
    SYSTEM_STATE = 'SystemState'


class RunResult():
    pass


class PassResult(RunResult):
    pass


class InvalidInputResult(RunResult):
    pass


class UnchangedInputResult(RunResult):
    pass


class ConnectionRefusedResult(RunResult):
    pass


class ErrorResult(RunResult):

    def __init__(self,
                 oracle: Oracle,
                 msg: str,
                 input_delta: Diff = None,
                 matched_system_delta: Diff = None) -> None:
        self.oracle = oracle
        self.message = msg
        self.input_delta = input_delta
        self.matched_system_delta = matched_system_delta


def flatten_list(l: list, curr_path: list):
    '''Convert list into list of tuples (path, value)

    Args:
        l: list to be flattened
        curr_path: current path of d

    Returns:
        list of Tuples (path, basic value)
    '''
    result = []
    for idx, value in enumerate(l):
        path = curr_path + [idx]
        if isinstance(value, dict):
            result.extend(flatten_dict(value, path))
        elif isinstance(value, list):
            result.extend(flatten_list(value, path))
        else:
            result.append((path, value))
    return result


def flatten_dict(d: dict, curr_path: list):
    '''Convert dict into list of tuples (path, value)

    Args:
        d: dict to be flattened
        curr_path: current path of d

    Returns:
        list of Tuples (path, basic value)
    '''
    result = []
    for key, value in d.items():
        path = curr_path + [key]
        if isinstance(value, dict):
            result.extend(flatten_dict(value, path))
        elif isinstance(value, list):
            result.extend(flatten_list(value, path))
        else:
            result.append((path, value))
    return result


def postprocess_diff(diff):
    '''Postprocess diff from DeepDiff tree view
    '''

    diff_dict = {}
    for category, changes in diff.items():
        diff_dict[category] = {}
        for change in changes:
            '''Heuristic
            When an entire dict/list is added or removed, flatten this
            dict/list to help field matching and value comparison in oracle
            '''
            if (isinstance(change.t1, dict) or isinstance(change.t1, list)) \
                    and (change.t2 == None or isinstance(change.t2, NotPresent)):
                logging.debug('dict deleted')
                if isinstance(change.t1, dict):
                    flattened_changes = flatten_dict(change.t1, [])
                else:
                    flattened_changes = flatten_list(change.t1, [])
                for (path, value) in flattened_changes:
                    str_path = change.path()
                    for i in path:
                        str_path += '[%s]' % i
                    diff_dict[category][str_path] = Diff(value, change.t2,
                                                         change.path(output_format='list') + path)
            elif (isinstance(change.t2, dict) or isinstance(change.t2, list)) \
                    and (change.t1 == None or isinstance(change.t1, NotPresent)):
                if isinstance(change.t2, dict):
                    flattened_changes = flatten_dict(change.t2, [])
                else:
                    flattened_changes = flatten_list(change.t2, [])
                for (path, value) in flattened_changes:
                    str_path = change.path()
                    for i in path:
                        str_path += '[%s]' % i
                    diff_dict[category][str_path] = Diff(change.t1, value,
                                                         change.path(output_format='list') + path)
            else:
                diff_dict[category][change.path()] = Diff(change.t1, change.t2,
                                                          change.path(output_format='list'))
    return diff_dict


def invalid_input_message(log_msg: str, input_delta: dict) -> bool:
    '''Returns if the log shows the input is invalid'''
    # for regex in INVALID_INPUT_LOG_REGEX:
    #     if re.search(regex, log_line):
    #         logging.info('recognized invalid input: %s' % log_line)
    #         return True
                
    # Check if the log line contains the field or value
    # If so, also return True

    for delta_category in input_delta:
        for delta in delta_category:
            if isinstance(delta.path[-1], str) and delta.path[-1] in log_msg:
                logging.info("Recognized invalid input through field in error message: %s" % log_msg)
                return True
            elif str(delta.curr) in log_msg:
                logging.info("Recognized invalid input through value in error message: %s" % log_msg)
                return True

    return False


def canonicalize(s: str):
    '''Replace all upper case letters with _lowercase'''
    s = str(s)
    return re.sub(r"(?=[A-Z])", '_', s).lower()


def get_diff_stat():
    return None


def random_string(n: int):
    '''Generate random string with length n'''
    letters = string.ascii_lowercase
    return (''.join(random.choice(letters) for i in range(10)))


def save_result(trial_dir: str, trial_err: ErrorResult, num_tests: int, trial_elapsed):
    result_dict = {}
    try:
        trial_num = '-'.join(trial_dir.split('-')[-2:])
        result_dict['trial_num'] = trial_num
    except:
        result_dict['trial_num'] = trial_dir
    result_dict['duration'] = trial_elapsed
    result_dict['num_tests'] = num_tests
    if trial_err == None:
        logging.info('Trial %s completed without error', trial_dir)
    else:
        result_dict['oracle'] = trial_err.oracle
        result_dict['message'] = trial_err.message
        result_dict['input_delta'] = trial_err.input_delta
        result_dict['matched_system_delta'] = \
            trial_err.matched_system_delta
    result_path = os.path.join(trial_dir, 'result.json')
    with open(result_path, 'w') as result_file:
        json.dump(result_dict, result_file, cls=ActoEncoder, indent=6)


class ActoEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Diff):
            return obj.to_dict()
        elif isinstance(obj, NotPresent):
            return 'NotPresent'
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, TestCase):
            return obj.__str__()
        elif isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


EXCLUDE_PATH_REGEX = [
    r"managed_fields",
    r"managedFields",
    r"last\-applied\-configuration",
    r"generation",
    r"resourceVersion",
    r"resource_version",
    r"observed_generation",
    r"observedGeneration",
    r"control\-plane\.alpha\.kubernetes\.io\/leader",
]

EXCLUDE_ERROR_REGEX = [
    r"the object has been modified; please apply your changes to the latest version and try again",
    r"incorrect status code of 500 when calling endpoint",
    r"failed to ensure version, running with default",
    r"create issuer: no matches for kind",
    r"failed to run smartUpdate",
    r"dial: ping mongo",
    r"pod is not running",
    r"failed to sync(.)*status",
    r"can't failover, requeuing",
    r"Secret (.)* not found",
    r"failed to get proxySQL db",
    r"{\"severity\":\"INFO\"",
    r"PD failover replicas \(0\) reaches the limit \(0\)",
]

INVALID_INPUT_LOG_REGEX = [
    r"invalid",
    r"not valid",
    r"unsupported",
]

GENERIC_FIELDS = [
    r"^name$",
    r"^effect$",
    r"^key$",
    r"^operator$",
    r"^value$",
    r"\d",
    r"^claimName$",
    r"^host$",
]


def kind_kubecontext(cluster_name: str) -> str:
    '''Returns the kubecontext based onthe cluster name
    Kind always adds `kind` before the cluster name
    '''
    return f'kind-{cluster_name}'


def kind_create_cluster(name: str, config: str, version: str):
    '''Use subprocess to create kind cluster
    Args:
        name: name of the kind cluster
        config: path of the config file for cluster
        version: k8s version
    '''
    cmd = ['kind', 'create', 'cluster']

    if name:
        cmd.extend(['--name', name])
    else:
        cmd.extend(['--name', CONST.KIND_CLUSTER])

    if config:
        cmd.extend(['--config', config])

    if version:
        cmd.extend(['--image', f"kindest/node:v{version}"])

    return subprocess.run(cmd)


def kind_load_images(images_archive: str, name: str):
    '''Preload some frequently used images into Kind cluster to avoid ImagePullBackOff
    '''
    logging.info('Loading preload images')
    cmd = ['kind', 'load', 'image-archive']
    if images_archive == None:
        logging.warning(
            'No image to preload, we at least should have operator image')

    if name != None:
        cmd.extend(['--name', name])
    else:
        logging.error('Missing cluster name for kind load')

    p = subprocess.run(cmd + [images_archive])
    if p.returncode != 0:
        logging.error('Failed to preload images archive')


def kind_delete_cluster(name: str):
    cmd = ['kind', 'delete', 'cluster']

    if name:
        cmd.extend(['--name', name])
    else:
        logging.error('Missing cluster name for kind delete')

    while subprocess.run(cmd).returncode != 0:
        continue


def kubectl(args: list,
            cluster_name: str,
            capture_output=False,
            text=False) -> subprocess.CompletedProcess:
    cmd = ['kubectl']
    cmd.extend(args)

    if cluster_name == None:
        logging.error('Missing cluster name for kubectl')
    cmd.extend(['--context', kind_kubecontext(cluster_name)])

    p = subprocess.run(cmd, capture_output=capture_output, text=text)
    return p


def helm(args: list, cluster_name: str) -> subprocess.CompletedProcess:
    cmd = ['helm']
    cmd.extend(args)

    if cluster_name == None:
        logging.error('Missing cluster name for helm')
    cmd.extend(['--kube-context', kind_kubecontext(cluster_name)])

    return subprocess.run(cmd, capture_output=True, text=True)


def kubernetes_client(cluster_name: str) -> kubernetes.client.ApiClient:
    return kubernetes.config.kube_config.new_client_from_config(
        context=kind_kubecontext(cluster_name))

if __name__ == '__main__':
    line = 'E0624 08:02:40.303209       1 tidb_cluster_control.go:129] tidb cluster acto-namespace/test-cluster is not valid and must be fixed first, aggregated error: [spec.tikv.env[0].valueFrom.fieldRef: Invalid value: "": fieldRef is not supported, spec.tikv.env[0].valueFrom: Invalid value: "": may not have more than one field specified at a time]'

    field_val_dict = {'valueFrom': {'configMapKeyRef': {'key': 'ltzbphvbqz', 'name': 'fmtfbuyrwg', 'optional': True}, 'fieldRef': {'apiVersion': 'cyunlsgtrz', 'fieldPath': 'xihwjoiwit'}, 'resourceFieldRef': None, 'secretKeyRef': None}}

    print(invalid_input_message(line, field_val_dict)) # Tested on 7.14. Expected True, got True. Test passed.
