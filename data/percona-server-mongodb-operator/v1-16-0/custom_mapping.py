import builtins
import json
from typing import Any

import yaml
from typing_extensions import Self

from acto.input.input import CustomPropertySchemaMapping
from acto.input.test_generators.generator import test_generator
from acto.input.test_generators.stateful_set import replicas_tests
from acto.schema.base import BaseSchema
from acto.schema.under_specified import UnderSpecifiedSchema


def eliminate_null(value: Any) -> Any:
    """Eliminate null values from the dictionary"""
    match type(value):
        case builtins.dict:
            new_value = {}
            for key, val in value.items():
                if val is not None:
                    new_value[key] = eliminate_null(val)
            return new_value
        case builtins.list:
            return [eliminate_null(item) for item in value if item is not None]
        case _:
            return value


class MongodConfigSchema(UnderSpecifiedSchema):
    """Under-specified schema for pd.config"""

    def encode(self, value: dict) -> str:
        if value is None:
            return None
        return yaml.dump(eliminate_null(value))

    def decode(self, value: str) -> dict:
        return yaml.safe_load(value)

    @classmethod
    def from_original_schema(cls, original_schema: BaseSchema) -> Self:
        with open(
            "data/percona-server-mongodb-operator/v1-16-0/mongod-config.json",
            "r",
            encoding="utf-8",
        ) as file:
            config_schema = json.load(file)

        return cls(
            original_schema.path, original_schema.raw_schema, config_schema
        )


CUSTOM_PROPERTY_SCHEMA_MAPPING = [
    CustomPropertySchemaMapping(
        schema_path=["spec", "replsets", "ITEM", "configuration"],
        custom_schema=MongodConfigSchema,
    )
]

test_generator(property_name="size")(replicas_tests)
