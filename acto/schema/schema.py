from acto.utils import get_thread_logger

from .anyof import AnyOfSchema
from .array import ArraySchema
from .base import BaseSchema
from .boolean import BooleanSchema
from .integer import IntegerSchema
from .number import NumberSchema
from .object import ObjectSchema
from .oneof import OneOfSchema
from .opaque import OpaqueSchema
from .string import StringSchema


def extract_schema(path: list, schema: dict) -> BaseSchema:
    """Extract a schema from a dict"""

    logger = get_thread_logger(with_prefix=True)

    if "anyOf" in schema:
        return AnyOfSchema(path, schema)
    elif "oneOf" in schema:
        return OneOfSchema(path, schema)

    if "type" not in schema:
        if "properties" in schema:
            return ObjectSchema(path, schema)
        else:
            logger.warning("No type found in schema: %s", str(schema))
            return OpaqueSchema(path, schema)
    t = schema["type"]
    if isinstance(t, list):
        if "null" in t:
            t.remove("null")
        if len(t) == 1:
            t = t[0]

    if t == "string":
        return StringSchema(path, schema)
    elif t == "number":
        return NumberSchema(path, schema)
    elif t == "integer":
        return IntegerSchema(path, schema)
    elif t == "boolean":
        return BooleanSchema(path, schema)
    elif t == "array":
        return ArraySchema(path, schema)
    elif t == "object":
        return ObjectSchema(path, schema)
    else:
        raise RuntimeError(f"Unknown type: {t}")
