import builtins
import json
from typing import Any

from typing_extensions import Self

from acto.input.input import CustomPropertySchemaMapping
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


class KafkaConfigSchema(UnderSpecifiedSchema):
    """Under-specified schema for tidb.config"""

    def encode(self, value: dict) -> dict:
        if value is None:
            return None
        return eliminate_null(value)

    def decode(self, value: dict) -> dict:
        return value

    @classmethod
    def from_original_schema(cls, original_schema: BaseSchema) -> Self:
        with open(
            "data/strimzi-kafka-operator/v0-45-0/broker_config.json",
            "r",
            encoding="utf-8",
        ) as file:
            config_schema = json.load(file)

        return cls(
            original_schema.path, original_schema.raw_schema, config_schema
        )

    def __getitem__(self, key):
        return self.underlying_schema[key]

    def __setitem__(self, key, value):
        self.underlying_schema[key] = value


CUSTOM_PROPERTY_SCHEMA_MAPPING = [
    CustomPropertySchemaMapping(
        schema_path=["spec", "kafka", "config"], custom_schema=KafkaConfigSchema
    )
]
