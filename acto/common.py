import enum
import json
import operator
import random
import re
import string
import subprocess
from abc import abstractmethod
from datetime import datetime
from typing import List, Tuple, Any, Dict

import kubernetes
from deepdiff import DeepDiff
from deepdiff.helper import NotPresent

from acto.config import actoConfig
from .utils import get_thread_logger

class Diff:

    def __init__(self, prev, curr, path) -> None:
        # self.path = path
        self._prev = prev
        self._curr = curr
        self._path = path

    @property
    def prev(self) -> Any:
        return self._prev

    @property
    def curr(self) -> Any:
        return self._curr

    @property
    def path(self) -> List[str]:
        return self._path

    def to_dict(self) -> dict:
        '''serialize Diff object
        '''
        return {'prev': self.prev, 'curr': self.curr, 'path': self.path}

    def from_dict(dict) -> 'Diff':
        '''deserialize Diff object
        '''
        return Diff(**dict)


class Oracle(str, enum.Enum):
    ERROR_LOG = 'ErrorLog'
    SYSTEM_STATE = 'SystemState'
    SYSTEM_HEALTH = 'SystemHealth'
    RECOVERY = 'Recovery'
    CRASH = 'Crash'
    CUSTOM = 'Custom'


class RunResult:

    def __init__(self, revert, generation: int, testcase_signature: dict) -> None:
        self.crash_result: OracleResult = None
        self.input_result: OracleResult = None
        self.health_result: OracleResult = None
        self.state_result: OracleResult = None
        self.log_result: OracleResult = None
        self.custom_result: OracleResult = None
        self.misc_result: OracleResult = None
        self.recovery_result: OracleResult = None
        self.other_results: Dict[str, OracleResult] = {}

        self.generation = generation

        self.revert = revert
        self.testcase_signature = testcase_signature

    def set_result(self, result_name:str, value: 'OracleResult'):
        # TODO, store all results in a dict
        if result_name == 'crash':
            self.crash_result = value
        elif result_name == 'input':
            self.input_result = value
        elif result_name == 'health':
            self.health_result = value
        elif result_name == 'state':
            self.state_result = value
        elif result_name == 'log':
            self.log_result = value
        else:
            self.other_results[result_name] = value
            self.custom_result = value


    def is_pass(self) -> bool:
        if not isinstance(self.crash_result, PassResult) and self.crash_result is not None:
            return False
        elif not isinstance(self.health_result, PassResult) and self.health_result is not None:
            return False
        elif not isinstance(self.custom_result, PassResult) and self.custom_result is not None:
            return False

        if isinstance(self.state_result, PassResult):
            return True
        else:
            if actoConfig.alarms.invalid_input and isinstance(
                    self.log_result, InvalidInputResult):
                return True
            else:
                return False

    def is_invalid(self) -> Tuple[bool, 'InvalidInputResult']:
        if isinstance(self.input_result, InvalidInputResult):
            return True, self.input_result
        elif isinstance(self.log_result, InvalidInputResult):
            return True, self.log_result
        elif isinstance(self.misc_result, InvalidInputResult):
            return True, self.misc_result
        else:
            return False, None

    def is_connection_refused(self) -> bool:
        return isinstance(self.input_result, ConnectionRefusedResult)

    def is_unchanged(self) -> bool:
        return isinstance(self.input_result, UnchangedInputResult)

    def is_error(self) -> bool:
        if isinstance(self.crash_result, ErrorResult):
            return True
        elif isinstance(self.health_result, ErrorResult):
            return True
        elif isinstance(self.custom_result, ErrorResult):
            return True
        elif isinstance(self.recovery_result, ErrorResult):
            return True
        elif not isinstance(self.state_result, ErrorResult):
            return False
        else:
            if actoConfig.alarms.invalid_input and isinstance(
                    self.log_result, InvalidInputResult):
                return False
            else:
                return True

    def is_basic_error(self) -> bool:
        if isinstance(self.crash_result, ErrorResult):
            return True
        elif isinstance(self.health_result, ErrorResult):
            return True
        elif isinstance(self.custom_result, ErrorResult):
            return True
        elif isinstance(self.recovery_result, ErrorResult):
            return True
        else:
            return False

    def to_dict(self):
        '''serialize RunResult object
        '''
        return {
            'revert': self.revert,
            'generation': self.generation,
            'testcase': self.testcase_signature,
            'crash_result': self.crash_result.to_dict() if self.crash_result else None,
            'input_result': self.input_result.to_dict() if self.input_result else None,
            'health_result': self.health_result.to_dict() if self.health_result else None,
            'state_result': self.state_result.to_dict() if self.state_result else None,
            'log_result': self.log_result.to_dict() if self.log_result else None,
            'custom_result': self.custom_result.to_dict() if self.custom_result else None,
            'misc_result': self.misc_result.to_dict() if self.misc_result else None,
            'recovery_result': self.recovery_result.to_dict() if self.recovery_result else None
        }

    def from_dict(d: dict) -> 'RunResult':
        '''deserialize RunResult object
        '''

        result = RunResult(d['revert'], d['generation'], d['testcase'])
        result.crash_result = oracle_result_from_dict(d['crash_result'])
        result.input_result = oracle_result_from_dict(d['input_result'])
        result.health_result = oracle_result_from_dict(d['health_result'])
        result.state_result = oracle_result_from_dict(d['state_result'])
        result.log_result = oracle_result_from_dict(d['log_result'])
        result.custom_result = oracle_result_from_dict(d['custom_result'])
        result.misc_result = oracle_result_from_dict(d['misc_result'])
        result.recovery_result = oracle_result_from_dict(d['recovery_result'])
        return result


class OracleResult:

    @abstractmethod
    def to_dict(self):
        '''serialize OracleResult object
        '''
        return {}


class PassResult(OracleResult):

    def to_dict(self):
        return 'Pass'


class InvalidInputResult(OracleResult):

    def __init__(self, responsible_field: list) -> None:
        self.responsible_field = responsible_field

    def to_dict(self):
        return {'responsible_field': self.responsible_field}


class UnchangedInputResult(OracleResult):

    def to_dict(self):
        return 'UnchangedInput'


class ConnectionRefusedResult(OracleResult):

    def to_dict(self):
        return 'ConnectionRefused'


class ErrorResult(OracleResult, Exception):

    def __init__(self, oracle: Oracle, msg: str) -> None:
        self.oracle = oracle
        self.message = msg

    def to_dict(self):
        return {'oracle': self.oracle, 'message': self.message}

    def from_dict(d: dict):
        return ErrorResult(d['oracle'], d['message'])


class StateResult(ErrorResult):

    def __init__(self, oracle: Oracle, msg: str, input_delta: Diff = None, matched_system_delta: Diff = None) -> None:
        super().__init__(oracle, msg)
        self.input_delta = input_delta
        self.matched_system_delta = matched_system_delta

    def to_dict(self):
        return {
            'oracle':
                self.oracle,
            'message':
                self.message,
            'input_delta':
                self.input_delta.to_dict() if self.input_delta else None,
            'matched_system_delta':
                self.matched_system_delta.to_dict() if self.matched_system_delta else None
        }

    def from_dict(d: dict) -> 'StateResult':
        result = StateResult(d['oracle'], d['message'])
        result.input_delta = Diff.from_dict(d['input_delta']) if d['input_delta'] else None
        result.matched_system_delta = Diff.from_dict(
            d['matched_system_delta']) if d['matched_system_delta'] else None
        return result


class UnhealthyResult(ErrorResult):

    def __init__(self, oracle: Oracle, msg: str) -> None:
        super().__init__(oracle, msg)

    def to_dict(self):
        return {'oracle': self.oracle, 'message': self.message}

    def from_dict(d: dict):
        return UnhealthyResult(d['oracle'], d['message'])


class RecoveryResult(ErrorResult):

    def __init__(self, delta, from_, to_) -> None:
        self.oracle = Oracle.RECOVERY
        self.delta = delta
        self.from_ = from_
        self.to_ = to_

    def to_dict(self):
        return {
            'oracle':
                self.oracle,
            'delta':
                json.loads(self.delta.to_json(default_mapping={datetime: lambda x: x.isoformat()})),
            'from':
                self.from_,
            'to':
                self.to_
        }

    def from_dict(d: dict) -> 'RecoveryResult':
        result = RecoveryResult(d['delta'], d['from'], d['to'])
        return result


def oracle_result_from_dict(d: dict) -> OracleResult:
    if d == None:
        return PassResult()
    if d == 'Pass':
        return PassResult()
    elif d == 'UnchangedInput':
        return UnchangedInputResult()
    elif d == 'ConnectionRefused':
        return ConnectionRefusedResult()

    if 'responsible_field' in d:
        return InvalidInputResult(d['responsible_field'])
    elif 'oracle' in d:
        if d['oracle'] == Oracle.SYSTEM_STATE:
            return StateResult.from_dict(d)
        elif d['oracle'] == Oracle.SYSTEM_HEALTH:
            return UnhealthyResult.from_dict(d)
        elif d['oracle'] == Oracle.RECOVERY:
            return RecoveryResult.from_dict(d)
        elif d['oracle'] == Oracle.CRASH:
            return UnhealthyResult.from_dict(d)
        elif d['oracle'] == Oracle.CUSTOM:
            return ErrorResult.from_dict(d)

    raise ValueError('Invalid oracle result dict: {}'.format(d))


def flatten_list(l: list, curr_path: list) -> list:
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


def flatten_dict(d: dict, curr_path: list) -> list:
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
                if isinstance(change.t1, dict):
                    flattened_changes = flatten_dict(change.t1, [])
                else:
                    flattened_changes = flatten_list(change.t1, [])
                for (path, value) in flattened_changes:
                    if value == None or isinstance(value, NotPresent):
                        continue
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
                    if value == None or isinstance(value, NotPresent):
                        continue
                    str_path = change.path()
                    for i in path:
                        str_path += '[%s]' % i
                    diff_dict[category][str_path] = Diff(change.t1, value,
                                                         change.path(output_format='list') + path)
            else:
                diff_dict[category][change.path()] = Diff(change.t1, change.t2,
                                                          change.path(output_format='list'))
    return diff_dict


def invalid_input_message_regex(log_msg: List[str]) -> bool:
    '''Returns if the log shows the input is invalid

    Args:
        log_msg: message body of the log

    Returns:
        Tuple(bool, list):
            - if the log_msg indicates the input delta is invalid
            - when log indicates invalid input: the responsible field path for the invalid input
    '''
    logger = get_thread_logger(with_prefix=True)

    for line in log_msg:
        for regex in INVALID_INPUT_LOG_REGEX:
            if re.search(regex, line):
                logger.info('Recognized invalid input through regex: %s' % line)
                return True

    return False


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
    logger = get_thread_logger(with_prefix=True)

    for regex in INVALID_INPUT_LOG_REGEX:
        if re.search(regex, log_msg):
            logger.info('Recognized invalid input through regex: %s' % log_msg)
            return True, []

    # Check if the log line contains the field or value
    # If so, also return True

    for delta_category in input_delta.values():
        for delta in delta_category.values():
            if isinstance(delta.path[-1], str) and delta.path[-1] in log_msg:
                logger.info("Recognized invalid input through field [%s] in error message: %s" %
                            (delta.path[-1], log_msg))
                return True, delta.path

            # if delta.curr is an int, we do exact match to avoid matching a short
            # int (e.g. 1) to a log line and consider the int as invalid input
            elif isinstance(delta.curr, int):
                for item in log_msg.split(' '):
                    if item == str(delta.curr):
                        logger.info(
                            "Recognized invalid input through value [%s] in error message: %s" %
                            (delta.curr, log_msg))
                        return True, delta.path
            elif len(str(delta.curr)) > 1 and str(delta.curr) in log_msg:
                logger.info("Recognized invalid input through value [%s] in error message: %s" %
                            (str(delta.curr), log_msg))
                return True, delta.path

    return False, []


def canonicalize(s: str):
    '''Replace all upper case letters with _lowercase'''
    if isinstance(s, int):
        return 'ITEM'
    s = str(s)
    return re.sub(r"(?=[A-Z])", '_', s).lower()


def get_diff_stat():
    return None


def is_subfield(subpath: list, path: list) -> bool:
    '''Checks if subpath is a subfield of path
    '''
    if len(path) > len(subpath):
        return False
    for i in range(len(path)):
        if path[i] != subpath[i]:
            return False
    return True


def random_string(n: int):
    '''Generate random string with length n'''
    letters = string.ascii_lowercase
    return (''.join(random.choice(letters) for i in range(10)))


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
    r"no valid",
    r"unsupported",
    r"but expected",
    r"are not available",
    r"must include",
    r"must have",
    r"can't be empty",
]

GENERIC_FIELDS = [
    r"^name$",
    r"^effect$",
    r"^key$",
    r"^operator$",
    r"\d",
    r"^claimName$",
    r"^host$",
    r"^type$",
]


def helm(args: list, context_name: str) -> subprocess.CompletedProcess:
    logger = get_thread_logger(with_prefix=False)

    cmd = ['helm']
    cmd.extend(args)

    if context_name == None:
        logger.error('Missing cluster name for helm')
    cmd.extend(['--kube-context', context_name])

    return subprocess.run(cmd, capture_output=True, text=True)


def kubernetes_client(kubeconfig: str, context_name: str) -> kubernetes.client.ApiClient:
    return kubernetes.config.kube_config.new_client_from_config(config_file=kubeconfig,
                                                                context=context_name)

def print_event(msg: str):
    print(msg)

if __name__ == '__main__':
    line = "sigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).Start.func2.2/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:214"
    prev_input = curr_input = {'spec': {'tolerations': {}}}
    curr_input = {'spec': {'tolerations': {'tolerationSeconds': 1}}}
    input_delta = postprocess_diff(
        DeepDiff(prev_input, curr_input, ignore_order=True, report_repetition=True, view='tree'))
    print(invalid_input_message(line, input_delta))
