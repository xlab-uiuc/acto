import json
from typing import Any

import tomlkit
import tomlkit.container
import tomlkit.items


def toml_item_to_json_schema(
    item: tomlkit.container.Item,
) -> dict:
    """Converts a toml item to a json schema"""

    schema = {}
    match type(item):
        case tomlkit.items.Table:
            assert isinstance(item.value, tomlkit.container.Container)
            schema = process_container(item.value)
        case tomlkit.items.Bool:
            schema = {
                "type": "boolean",
                "default": item.value,
            }
        case tomlkit.items.Integer:
            schema = {
                "type": "integer",
                "default": item.value,
                "enum": [item.value],
            }
        case tomlkit.items.Float:
            schema = {
                "type": "number",
                "default": item.value,
                "enum": [item.value],
            }
        case tomlkit.items.String:
            schema = {
                "type": "string",
                "default": item.value if item.value != "NONE" else None,
                "enum": [item.value],
            }
        case tomlkit.items.Array:
            assert isinstance(item, tomlkit.items.Array)
            schema = process_array(item)

    return schema


def process_container(container: tomlkit.container.Container) -> dict:
    """Processes a toml container

    Returns a json schema
    """
    schema: dict[str, Any] = {
        "type": "object",
    }
    properties = {}
    buf: list[tomlkit.container.Item] = []
    for k, v in container.body:
        if isinstance(v, tomlkit.items.Whitespace):
            buf = []
        else:
            buf.append(v)
            if k is not None:
                properties[k.as_string().strip()] = process_chunk(buf)
                buf = []
    schema["properties"] = properties
    return schema


def process_array(array: tomlkit.items.Array) -> dict:
    """Processes a toml array

    Returns a json schema
    """
    schema = {
        "type": "array",
        "items": {},
        "default": array.value,
        "enum": [array.value],
    }
    if len(array.value) > 0:
        schema["items"] = process_chunk(array[0])
    return schema


def process_chunk(items: list[tomlkit.container.Item]) -> dict:
    """Processes a list of items which starts with a list of comments and
    end with a toml data item

    Returns a json schema
    """
    schema = {}
    description = ""
    for item in items:
        if isinstance(item, tomlkit.items.Comment):
            description += str(item.value)[1:].strip()
        else:
            schema = toml_item_to_json_schema(item)
            schema["description"] = description
    return schema


with open("mongodb.toml", "r", encoding="utf-8") as file:
    doc = tomlkit.load(fp=file)

    with open("crd.json", "w", encoding="utf-8") as file:
        json.dump(process_container(doc), file, indent=4)
