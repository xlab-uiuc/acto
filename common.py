from typing import Tuple, Optional
import enum
import json
from deepdiff.helper import NotPresent
from datetime import datetime, date

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
            diff_dict[category][change.path()] = Diff(change.t1, change.t2)
            if change.path() not in diff_dict:
                diff_stat[change.path()] = 1
            else:
                diff_stat[change.path()] += 1
    return diff_dict


def get_diff_stat():
    return diff_stat


class Diff:

    def __init__(self, prev, curr, type='') -> None:
        # self.path = path
        self.prev = prev
        self.curr = curr
        self.type = type

    def to_dict(self):
        '''serialize Diff object
        '''
        return {'prev': self.prev, 'curr': self.curr, 'type': self.type}


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
]
