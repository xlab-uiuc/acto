import enum
import json
import os
from typing import Tuple
from deepdiff.helper import NotPresent
from datetime import datetime, date
import re
import logging
import string
import random
import subprocess
import kubernetes
import requests
import operator

from test_case import TestCase
from deepdiff import DeepDiff


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

    def __init__(self, deploy: DeployConfig, crd_name: str, custom_fields: str, example_dir: str,
                 context: str, seed_custom_resource: str, source_path: str,
                 analysis: AnalysisConfig) -> None:
        self.deploy = deploy
        self.crd_name = crd_name
        self.custom_fields = custom_fields
        self.example_dir = example_dir
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
    SYSTEM_HEALTH = 'SystemHealth'


class RunResult():
    pass


class PassResult(RunResult):
    pass


class InvalidInputResult(RunResult):

    def __init__(self, responsible_field: list) -> None:
        self.responsible_field = responsible_field


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


def invalid_input_message(log_msg: str, input_delta: dict) -> Tuple[bool, list]:
    '''Returns if the log shows the input is invalid

    Args:
        log_msg: message body of the log
        input_delta: the input delta we applied to the CR

    Returns:
        Tuple(bool, list):
            - if the log_msg indicates the input delta is invalid
            - when log indicates invalid input: the responsible field path for the invalid input
    '''
    for regex in INVALID_INPUT_LOG_REGEX:
        if re.search(regex, log_msg):
            logging.info(
                'Recognized invalid input through regex: %s' % log_msg)
            return True, None

    # Check if the log line contains the field or value
    # If so, also return True

    for delta_category in input_delta.values():
        for delta in delta_category.values():
            if isinstance(delta.path[-1], str) and delta.path[-1] in log_msg:
                logging.info("Recognized invalid input through field [%s] in error message: %s" %
                             (delta.path[-1], log_msg))
                return True, delta.path
            # if delta.curr is an int, we do exact match to avoid matching a short
            # int (e.g. 1) to a log line and consider the int as invalid input
            elif isinstance(delta.curr, int):
                for item in log_msg.split(' '):
                    if item == str(delta.curr):
                        logging.info("Recognized invalid input through value [%s] in error message: %s" % (
                            delta.curr, log_msg))
                        return True, delta.path
            elif str(delta.curr) in log_msg:
                logging.info("Recognized invalid input through value [%s] in error message: %s" %
                             (str(delta.curr), log_msg))
                return True, delta.path

    return False, None


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


def translate_op(input_op: str):
    if input_op == '!=':
        op = operator.ne
    elif input_op == '==':
        op = operator.eq
    elif input_op == '<=':
        op = operator.le
    elif input_op == '<':
        op = operator.lt
    elif input_op == '>=':
        op = operator.ge
    elif input_op == '>':
        op = operator.gt
    else:
        raise ValueError('Unknown operator: %s' % input_op)

    return op


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
    r"{\"level\":\"info\"",
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


def kubectl(args: list,
            context_name: str,
            capture_output=False,
            text=False) -> subprocess.CompletedProcess:
    cmd = ['kubectl']
    cmd.extend(args)

    if context_name == None:
        logging.error('Missing context name for kubectl')
    cmd.extend(['--context', context_name])

    p = subprocess.run(cmd, capture_output=capture_output, text=text)
    return p


def helm(args: list, context_name: str) -> subprocess.CompletedProcess:
    cmd = ['helm']
    cmd.extend(args)

    if context_name == None:
        logging.error('Missing cluster name for helm')
    cmd.extend(['--kube-context', context_name])

    return subprocess.run(cmd, capture_output=True, text=True)


def kubernetes_client(context_name: str) -> kubernetes.client.ApiClient:
    return kubernetes.config.kube_config.new_client_from_config(
        context=context_name)


if __name__ == '__main__':
    line = "sigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).Start.func2.2/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:214"
    prev_input = curr_input = {
        'spec': {
            'tolerations': {}
        }
    }
    curr_input = {
        'spec': {
            'tolerations': {
                'tolerationSeconds': 1
            }
        }
    }
    input_delta = postprocess_diff(
        DeepDiff(prev_input, curr_input, ignore_order=True, report_repetition=True,
                 view='tree'))
    print(invalid_input_message(line, input_delta))
