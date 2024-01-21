"""This module provides a decorator for generating test cases for a schema and
a function to get all test cases for a schema."""

from dataclasses import dataclass
from typing import Callable, Literal, Optional

import pydantic

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


@dataclass
class TestGenerator:
    """A test generator object"""

    k8s_schema_name: Optional[str]
    field_name: Optional[str]
    field_type: Optional[
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
    priority: int
    func: Callable[[BaseSchema], list[TestCase]]


# singleton
# global variable for registered test generators
TEST_GENERATORS: list[TestGenerator] = []


def generator(
    k8s_schema_name: Optional[str] = None,
    field_name: Optional[str] = None,
    field_type: Optional[
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
    priority: int = 0,
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
        or field_name is not None
        or field_type is not None
        or paths is not None
    ), "One of k8s_schema_name, schema_name, schema_type, paths must be specified"

    def wrapped_func(func: Callable[[BaseSchema], list[TestCase]]):
        func = pydantic.validate_call(func)
        gen_obj = TestGenerator(
            k8s_schema_name,
            field_name,
            field_type,
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
        schema: BaseSchema, field_name: Optional[str]
    ) -> list[tuple[list[str], list[TestCase]]]:
        # print(schema_name, schema.path, type(schema))
        test_cases: list[tuple[list[str], list[TestCase]]] = []
        generator_candidates: list[TestGenerator] = []
        # check paths
        path_str = "/".join(schema.path)
        matched_schema = matched_schemas_dict.get(path_str)
        for test_generator in TEST_GENERATORS:
            # check paths
            for path in test_generator.paths or []:
                if path_str.endswith(path):
                    generator_candidates.append(test_generator)
                    continue

            # check field name
            if (
                test_generator.field_name is not None
                and test_generator.field_name == field_name
            ):
                generator_candidates.append(test_generator)
                continue

            # check k8s schema name
            if (
                test_generator.k8s_schema_name is not None
                and matched_schema is not None
                and matched_schema.k8s_schema_name.endswith(
                    test_generator.k8s_schema_name
                )
            ):
                generator_candidates.append(test_generator)
                continue

            # check type
            if test_generator.field_type is not None:
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
                if schema_type_obj := matching_types.get(
                    test_generator.field_type
                ):
                    if isinstance(schema, schema_type_obj):
                        generator_candidates.append(test_generator)
                else:
                    raise ValueError(
                        f"Unknown schema type: {test_generator.field_type}"
                    )

        # sort by priority
        generator_candidates.sort(key=lambda x: x.priority, reverse=True)
        if len(generator_candidates) > 0:
            test_cases.append(
                (schema.path, generator_candidates[0].func(schema)),
            )

        # check sub schemas
        if isinstance(schema, ArraySchema):
            test_cases.extend(
                get_testcases_helper(schema.get_item_schema(), "ITEM")
            )
        elif isinstance(schema, ObjectSchema):
            for field, sub_schema in schema.properties.items():
                test_cases.extend(get_testcases_helper(sub_schema, field))
        return test_cases

    return get_testcases_helper(schema, None)
