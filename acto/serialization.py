import json
from datetime import date, datetime

import ordered_set
from deepdiff import DeepDiff
from deepdiff.helper import NotPresent

from acto.common import Diff, PropertyPath
from acto.input import TestCase
from acto.result import DifferentialOracleResult


class ActoEncoder(json.JSONEncoder):
    """Encoder for acto oects"""

    def default(self, o):
        """Default encoder"""

        if hasattr(o, "serialize"):
            return o.serialize()

        if isinstance(o, Diff):
            return o.to_dict()
        elif isinstance(o, NotPresent):
            return "NotPresent"
        elif isinstance(o, (datetime, date)):
            return o.isoformat()
        elif isinstance(o, TestCase):
            return str(o)
        elif isinstance(o, set):
            return list(o)
        elif isinstance(o, ordered_set.OrderedSet):
            return list(o)
        elif isinstance(o, DeepDiff):
            return o.to_dict()
        elif isinstance(o, PropertyPath):
            return str(o)
        elif isinstance(o, DifferentialOracleResult):
            return o.serialize()
        return json.JSONEncoder.default(self, o)


class ContextEncoder(json.JSONEncoder):
    """Encoder for context oects"""

    def default(self, o):
        if isinstance(o, set):
            return list(o)
        elif isinstance(o, str) and o == "true":
            return True
        elif isinstance(o, str) and o == "false":
            return False
        return json.JSONEncoder.default(self, o)
