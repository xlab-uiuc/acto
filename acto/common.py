import operator
import random
import re
import string
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Any

from deepdiff import DeepDiff
from deepdiff.helper import NotPresent

from .utils import get_thread_logger


@dataclass(frozen=True)
class Diff:
    prev: Any
    curr: Any
    path: List[str]

    def __eq__(self, other):
        def value_eq_with_not_present(foo, bar):
            if isinstance(foo, NotPresent):
                return isinstance(bar, NotPresent)
            return foo == bar

        return value_eq_with_not_present(self.prev, other.prev) and value_eq_with_not_present(self.curr, other.curr) and self.path == other.path

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
            # do not flatten empty list
            if not value:
                result.append((path, value))
            else:
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
            # do not flatten empty dict
            if value == {}:
                result.append((path, value))
            else:
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
    r"not supported",
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


def print_event(msg: str):
    print(msg)


if __name__ == '__main__':
    line = "sigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).Start.func2.2/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.9.6/pkg/internal/controller/controller.go:214"
    prev_input = curr_input = {'spec': {'tolerations': {}}}
    curr_input = {'spec': {'tolerations': {'tolerationSeconds': 1}}}
    input_delta = postprocess_diff(
        DeepDiff(prev_input, curr_input, ignore_order=True, report_repetition=True, view='tree'))
    print(invalid_input_message(line, input_delta))
