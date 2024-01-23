"""This module provides a decorator for generating test cases for a schema and
a function to get all test cases for a schema."""

import inspect
from dataclasses import dataclass
from enum import IntEnum
from functools import wraps
from typing import Callable, Literal, Optional

import pytest

from acto.input.k8s_schemas import KubernetesObjectSchema
from acto.input.testcase import TestCase
from acto.schema import (
    AnyOfSchema,
    ArraySchema,
    BaseSchema,
    BooleanSchema,
    IntegerSchema,
    NumberSchema,
    ObjectSchema,
    OneOfSchema,
    OpaqueSchema,
    StringSchema,
)


class Priority(IntEnum):
    """Priority enum for test generators"""

    PRIMITIVE = 0
    SEMANTIC = 1
    CUSTOM = 2


@dataclass
class TestGenerator:
    """A test generator object"""

    k8s_schema_name: Optional[str]
    property_name: Optional[str]
    property_type: Optional[
        Literal[
            "AnyOf",
            "Array",
            "Boolean",
            "Integer",
            "Number",
            "Object",
            "OneOf",
            "Opaque",
            "String",
        ]
    ]
    paths: Optional[list[str]]
    priority: Priority
    func: Callable[[BaseSchema], list[TestCase]]

    def match(
        self,
        schema: BaseSchema,
        matched_schema: Optional[KubernetesObjectSchema],
    ) -> bool:
        """Check if the test generator matches the schema"""
        return all(
            [
                self._match_path(schema),
                self._match_property_name(schema),
                self._match_property_type(schema),
                self._match_k8s_schema_name(matched_schema),
            ]
        )

    def _match_path(self, schema: BaseSchema) -> bool:
        if not self.paths:
            return True
        path_str = "/".join(schema.path)
        return any(path_str.endswith(path) for path in self.paths)

    def _match_property_name(self, schema: BaseSchema) -> bool:
        return (
            self.property_name is None
            or len(schema.path) > 0
            and self.property_name == schema.path[-1]
        )

    def _match_property_type(self, schema: BaseSchema) -> bool:
        if self.property_type is None:
            return True
        matching_types = {
            "AnyOf": AnyOfSchema,
            "Array": ArraySchema,
            "Boolean": BooleanSchema,
            "Integer": IntegerSchema,
            "Number": NumberSchema,
            "Object": ObjectSchema,
            "OneOf": OneOfSchema,
            "Opaque": OpaqueSchema,
            "String": StringSchema,
        }
        if schema_type_obj := matching_types.get(self.property_type):
            if isinstance(schema, schema_type_obj):
                return True
        else:
            raise ValueError(f"Unknown schema type: {self.property_type}")
        return False

    def _match_k8s_schema_name(
        self, matched_schema: Optional[KubernetesObjectSchema]
    ) -> bool:
        return (
            self.k8s_schema_name is None
            or matched_schema is not None
            and matched_schema.k8s_schema_name.endswith(self.k8s_schema_name)
        )


# singleton
# global variable for registered test generators
TEST_GENERATORS: list[TestGenerator] = []


def validate_call(func: Callable) -> Callable:
    """Validates the `schema` argument type for call to a test generator
    function"""

    error_msg = (
        "Argument `schema` of function {} got type {} but expected type {}"
    )

    @wraps(func)
    def wrapped_func(*args, **kwargs):
        # TODO: handle parameter name other than `schema` and improve error msg
        if schema_arg := inspect.signature(func).parameters.get("schema"):
            if not isinstance(args[0], schema_arg.annotation):
                raise TypeError(
                    error_msg.format(func, schema_arg.annotation, type(args[0]))
                )
        return func(*args, **kwargs)

    return wrapped_func


@pytest.mark.skip(reason="not a test")
def test_generator(
    k8s_schema_name: Optional[str] = None,
    property_name: Optional[str] = None,
    property_type: Optional[
        Literal[
            "AnyOf",
            "Array",
            "Boolean",
            "Integer",
            "Number",
            "Object",
            "OneOf",
            "Opaque",
            "String",
        ]
    ] = None,
    paths: Optional[list[str]] = None,
    priority: Priority = Priority.CUSTOM,
):
    """Annotates a function as a test generator

    Args:
        k8s_schema_name (str, optional): Kubernetes schema name. Defaults to None.
        field_name (str, optional): field/property name. Defaults to None.
        field_type (str, optional): field/property type. Defaults to None.
        paths (list[str], optional): Path suffixes. Defaults to None.
        priority (int, optional): Priority. Defaults to 0."""
    assert (
        k8s_schema_name is not None
        or property_name is not None
        or property_type is not None
        or paths is not None
    ), "One of k8s_schema_name, schema_name, schema_type, paths must be specified"

    def wrapped_func(func: Callable[[BaseSchema], list[TestCase]]):
        func = validate_call(func)
        gen_obj = TestGenerator(
            k8s_schema_name,
            property_name,
            property_type,
            paths,
            priority,
            func,
        )
        TEST_GENERATORS.append(gen_obj)
        return func

    return wrapped_func


def get_testcases(
    schema: BaseSchema,
    matched_schemas: list[tuple[BaseSchema, KubernetesObjectSchema]],
) -> list[tuple[list[str], list[TestCase]]]:
    """Get all test cases for a schema from registered test generators"""
    matched_schemas_dict: dict[str, KubernetesObjectSchema] = {
        "/".join(s.path): m for s, m in matched_schemas
    }

    def get_testcases_helper(
        schema: BaseSchema,
    ) -> list[tuple[list[str], list[TestCase]]]:
        test_cases: list[tuple[list[str], list[TestCase]]] = []
        generator_candidates: list[TestGenerator] = []

        # check paths
        path_str = "/".join(schema.path)
        matched_schema = matched_schemas_dict.get(path_str)

        for test_generator_ in TEST_GENERATORS:
            if test_generator_.match(schema, matched_schema):
                generator_candidates.append(test_generator_)

        # sort by priority
        generator_candidates.sort(key=lambda x: x.priority, reverse=True)
        if len(generator_candidates) > 0:
            test_cases.append(
                (schema.path, generator_candidates[0].func(schema)),
            )

        # check sub schemas
        if isinstance(schema, ArraySchema):
            test_cases.extend(get_testcases_helper(schema.get_item_schema()))
        elif isinstance(schema, ObjectSchema):
            for sub_schema in schema.properties.values():
                test_cases.extend(get_testcases_helper(sub_schema))
        return test_cases

    return get_testcases_helper(schema)
