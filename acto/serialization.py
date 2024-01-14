import decimal
import json
import uuid
from datetime import date, datetime

import ordered_set
from deepdiff import DeepDiff
from deepdiff.helper import NotPresent

from acto.common import Diff, PropertyPath
from acto.input import TestCase
from acto.result import DifferentialOracleResult


def _serialize_decimal(value: decimal.Decimal):
    if value.as_tuple().exponent == 0:
        return int(value)
    else:
        return float(value)


class ActoEncoder(json.JSONEncoder):
    """Encoder for acto oects"""

    def default(self, o):
        """Default encoder"""

        # this section is for pydantic basemodels
        if hasattr(o, "serialize"):
            return o.serialize()

        # this section is from deepdiff
        if isinstance(o, ordered_set.OrderedSet):
            return list(o)
        if isinstance(o, decimal.Decimal):
            return _serialize_decimal(o)
        if isinstance(o, type):
            return o.__name__
        if isinstance(o, bytes):
            return o.decode("utf-8")
        if isinstance(o, uuid.UUID):
            return str(o)

        if isinstance(o, Diff):
            return o.to_dict()
        if isinstance(o, NotPresent):
            return "NotPresent"
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, TestCase):
            return str(o)
        if isinstance(o, set):
            return list(o)
        if isinstance(o, DeepDiff):
            return o.to_dict()
        if isinstance(o, PropertyPath):
            return str(o)
        if isinstance(o, DifferentialOracleResult):
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
