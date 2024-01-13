"""This module provides a decorator for generating test cases for a schema and
a function to get all test cases for a schema."""

from collections import namedtuple
from typing import Callable, Literal, Optional

from acto.input.k8s_schemas import KubernetesObjectSchema, KubernetesSchema
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

TestGenerator = namedtuple(
    "TestGeneratorObject",
    [
        "k8s_schema_name",
        "field_name",
        "field_type",
        "paths",
        "priority",
        "func",
    ],
)


# global variable for registered test generators
test_generators: TestGenerator = []


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
        gen_obj = TestGenerator(
            k8s_schema_name,
            field_name,
            field_type,
            paths,
            priority,
            func,
        )
        test_generators.append(gen_obj)
        return func

    return wrapped_func


def get_testcases(
    schema: BaseSchema,
    matched_schemas: [tuple[BaseSchema, KubernetesSchema]],
) -> list[tuple[list[str], TestCase]]:
    """Get all test cases for a schema from registered test generators"""
    matched_schemas: dict[str, KubernetesObjectSchema] = {
        "/".join(s.path): m for s, m in matched_schemas
    }

    def get_testcases_helper(schema: BaseSchema, field_name: Optional[str]):
        # print(schema_name, schema.path, type(schema))
        test_cases = []
        generator_candidates = []
        # check paths
        path_str = "/".join(schema.path)
        matched_schema = matched_schemas.get(path_str)
        for test_gen in test_generators:
            # check paths
            for path in test_gen.paths or []:
                if path_str.endswith(path):
                    generator_candidates.append(test_gen)
                    continue

            # check field name
            if (
                test_gen.field_name is not None
                and test_gen.field_name == field_name
            ):
                generator_candidates.append(test_gen)
                continue

            # check k8s schema name
            if (
                test_gen.k8s_schema_name is not None
                and matched_schema is not None
                and matched_schema.k8s_schema_name.endswith(
                    test_gen.k8s_schema_name
                )
            ):
                generator_candidates.append(test_gen)
                continue

            # check type
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
            if schema_type_obj := matching_types.get(test_gen.field_type):
                if isinstance(schema, schema_type_obj):
                    generator_candidates.append(test_gen)

        # sort by priority
        generator_candidates.sort(key=lambda x: x.priority, reverse=True)
        if len(generator_candidates) > 0:
            test_cases.append(
                (schema.path, generator_candidates[0].func(schema))
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
