import json

import tomlkit
from typing_extensions import Self

from acto.input.input import CustomPropertySchemaMapping
from acto.schema.base import BaseSchema
from acto.schema.under_specified import UnderSpecifiedSchema


class PdConfigSchema(UnderSpecifiedSchema):
    """Under-specified schema for pd.config"""

    def encode(self, value: dict) -> str:
        return tomlkit.dumps(value)

    def decode(self, value: str) -> dict:
        return tomlkit.loads(value)

    @classmethod
    def from_original_schema(cls, original_schema: BaseSchema) -> Self:
        with open(
            "data/tidb-operator/v1-6-0/pd_config.json", "r", encoding="utf-8"
        ) as file:
            config_schema = json.load(file)

        return cls(
            original_schema.path, original_schema.raw_schema, config_schema
        )


CUSTOM_PROPERTY_SCHEMA_MAPPING = [
    CustomPropertySchemaMapping(
        schema_path=["spec", "pd", "config"], custom_schema=PdConfigSchema
    )
]
