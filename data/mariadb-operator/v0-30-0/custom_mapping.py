import builtins
import configparser
import json
from typing import Any

import tomlkit
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


class MariaDBConfigSchema(UnderSpecifiedSchema):
    """Under-specified schema for tidb.config"""

    def encode(self, value: dict) -> str:
        if value is None:
            return None
        return tomlkit.dumps(eliminate_null(value))

    def decode(self, value: str) -> dict:
        config = configparser.ConfigParser()
        config.read_string(value)

        sections_dict = {}

        # get all defaults
        defaults = config.defaults()
        temp_dict = {}
        for key in defaults.keys():
            temp_dict[key] = defaults[key]

        sections_dict["default"] = temp_dict

        # get sections and iterate over each
        sections = config.sections()

        for section in sections:
            options = config.options(section)
            temp_dict = {}
            for option in options:
                temp_dict[option] = config.get(section, option)

            sections_dict[section] = temp_dict

        return sections_dict

    @classmethod
    def from_original_schema(cls, original_schema: BaseSchema) -> Self:
        with open(
            "data/mariadb-operator/v0-30-0/mariadb-config.json",
            "r",
            encoding="utf-8",
        ) as file:
            config_schema = json.load(file)

        return cls(
            original_schema.path, original_schema.raw_schema, config_schema
        )


CUSTOM_PROPERTY_SCHEMA_MAPPING = [
    CustomPropertySchemaMapping(
        schema_path=["spec", "myCnf"], custom_schema=MariaDBConfigSchema
    )
]
