import json
from datetime import date, datetime
from functools import wraps
from inspect import getfullargspec

from deepdiff import DeepDiff
from deepdiff.helper import NotPresent

from acto.common import Diff


# def store_function_return_value():
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             argspec = getfullargspec(func)
#             argument_index = argspec.args.index(argument_name)
#             return json.dumps(func(*args, **kwargs), cls=ActoEncoder)
#         return wrapper


class ActoEncoder(json.JSONEncoder):

    def default(self, obj):
        from acto.input import TestCase

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
        elif isinstance(obj, DeepDiff):
            return obj.to_json()
        return json.JSONEncoder.default(self, obj)


class ContextEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, str) and obj == 'true':
            return True
        elif isinstance(obj, str) and obj == 'false':
            return False
        return json.JSONEncoder.default(self, obj)