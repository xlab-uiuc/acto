import enum
import json
from deepdiff.helper import NotPresent
from datetime import datetime, date
import re
import logging
import string
import random

from test_case import TestCase


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
                    diff_dict[category][str_path] = Diff(
                        value, change.t2,
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
                    diff_dict[category][str_path] = Diff(
                        change.t1, value,
                        change.path(output_format='list') + path)
            else:
                diff_dict[category][change.path()] = Diff(
                    change.t1, change.t2, change.path(output_format='list'))
    return diff_dict


def invalid_input_message(log_line: str) -> bool:
    '''Returns if the log shows the input is invalid'''
    for regex in INVALID_INPUT_LOG_REGEX:
        if re.search(regex, log_line):
            logging.info('recognized invalid input: %s' % log_line)
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
]

INVALID_INPUT_LOG_REGEX = [
    r"is invalid",
]

GENERIC_FIELDS = [
    r"^name$",
    r"^effect$",
    r"^key$",
    r"^operator$",
    r"^value$",
    r"\d",
]