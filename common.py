from typing import Tuple, Optional
import enum
import json
from deepdiff.helper import NotPresent
from datetime import datetime, date
import re

ACTO_IDX_SKIP = 'ACTO-INGORE'
TYPE_CHANGE = 'TYPE-CHANGE'

diff_stat = {}


class RunResult(enum.Enum):
    passing = 0
    invalidInput = 1
    error = 2
    unchanged = 3


def postprocess_diff(diff):
    '''Postprocess diff from DeepDiff tree view
    '''

    diff_dict = {}
    for category, changes in diff.items():
        diff_dict[category] = {}
        for change in changes:
            # diff_dict[category].append(Diff(change.path(), change.t1, change.t2))
            diff_dict[category][change.path()] = Diff(
                change.t1, change.t2, change.path(output_format='list'))
            if change.path() not in diff_dict:
                diff_stat[change.path()] = 1
            else:
                diff_stat[change.path()] += 1
    return diff_dict


def canonicalize(s: str):
    '''Replace all upper case letters with _lowercase'''
    return re.sub(r"(?=[A-Z])", '_', s).lower()


def get_diff_stat():
    return diff_stat


class Diff:

    def __init__(self, prev, curr, path) -> None:
        # self.path = path
        self.prev = prev if not isinstance(prev, NotPresent) else None
        self.curr = curr if not isinstance(curr, NotPresent) else None
        self.path = path

    def to_dict(self):
        '''serialize Diff object
        '''
        return {'prev': self.prev, 'curr': self.curr}


class ActoEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Diff):
            return obj.to_dict()
        elif isinstance(obj, NotPresent):
            return None
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
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
]
