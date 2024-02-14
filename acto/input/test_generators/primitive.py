"""Testcase generators for primitive types"""

# pylint: disable=unused-argument, invalid-name, unused-variable

import random

import exrex

from acto.input.test_generators.generator import Priority, test_generator
from acto.input.testcase import EnumTestCase, SchemaPrecondition, TestCase
from acto.schema import (
    AnyOfSchema,
    ArraySchema,
    BaseSchema,
    BooleanSchema,
    IntegerSchema,
    ObjectSchema,
    OpaqueSchema,
    StringSchema,
)
from acto.utils.thread_logger import get_thread_logger


def resolve_testcases(schema: BaseSchema) -> list[TestCase]:
    """Get testcases for a schema"""
    if isinstance(schema, AnyOfSchema):
        return any_of_tests(schema)
    elif isinstance(schema, ArraySchema):
        return array_tests(schema)
    elif isinstance(schema, BooleanSchema):
        return boolean_tests(schema)
    elif isinstance(schema, IntegerSchema):
        return integer_tests(schema)
    # elif isinstance(schema, NumberSchema):
    #     return number_tests(schema)
    elif isinstance(schema, ObjectSchema):
        return object_tests(schema)
    elif isinstance(schema, OpaqueSchema):
        return []
    elif isinstance(schema, StringSchema):
        return string_tests(schema)
    else:
        raise NotImplementedError


@test_generator(property_type="AnyOf", priority=Priority.PRIMITIVE)
def any_of_tests(schema: AnyOfSchema):
    """Generate testcases for AnyOf type"""

    ret: list[TestCase] = []
    if schema.enum is not None:
        for case in schema.enum:
            ret.append(EnumTestCase(case, primitive=True))
    else:
        for sub_schema in schema.possibilities:
            testcases = resolve_testcases(sub_schema)
            for testcase in testcases:
                testcase.add_precondition(
                    SchemaPrecondition(sub_schema).precondition
                )
            ret.extend(testcases)
    return ret


@test_generator(property_type="Array", priority=Priority.PRIMITIVE)
def array_tests(schema: ArraySchema):
    """Representation of an array node

    It handles
        - minItems
        - maxItems
        - items
        - uniqueItems
    """
    default_min_items = 0
    default_max_items = 5

    DELETION_TEST = "array-deletion"
    PUSH_TEST = "array-push"
    POP_TEST = "array-pop"
    EMPTY_TEST = "array-empty"

    def push_precondition(prev):
        if prev is None:
            return False
        if len(prev) >= schema.max_items:
            return False
        return True

    def push_mutator(prev):
        new_item = schema.item_schema.gen()
        return prev + [new_item]

    def push_setup(prev):
        logger = get_thread_logger(with_prefix=True)
        if len(schema.examples) > 0:
            for example in schema.examples:
                if len(example) > 1:
                    logger.info(
                        "Using example for setting up field [%s]: [%s]",
                        schema.path,
                        schema.examples[0],
                    )
                    return example
        if prev is None:
            return schema.gen(minimum=True)
        return schema.gen(size=schema.min_items)

    def pop_precondition(prev):
        if prev is None:
            return False
        if len(prev) <= schema.min_items:
            return False
        if len(prev) == 0:
            return False
        return True

    def pop_mutator(prev):
        prev.pop()
        return prev

    def pop_setup(prev):
        logger = get_thread_logger(with_prefix=True)

        if len(schema.examples) > 0:
            for example in schema.examples:
                if len(example) > 1:
                    logger.info(
                        "Using example for setting up field [%s]: [%s]",
                        schema.path,
                        schema.examples[0],
                    )
                    return example
        if prev is None:
            return schema.gen(size=schema.min_items + 1)
        return schema.gen(size=schema.max_items)

    def empty_precondition(prev):
        return prev != []

    def empty_mutator(prev):
        return []

    def empty_setup(prev):
        return prev

    def delete(prev):
        return schema.empty_value()

    def delete_precondition(prev):
        return (
            prev is not None
            and prev != schema.default
            and prev != schema.empty_value()
        )

    def delete_setup(prev):
        logger = get_thread_logger(with_prefix=True)
        if len(schema.examples) > 0:
            logger.info(
                "Using example for setting up field [%s]: [%s]",
                schema.path,
                schema.examples[0],
            )
            example_without_default = [
                x for x in schema.enum if x != schema.default
            ]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return schema.gen(exclude_value=schema.default)
        else:
            return schema.gen(exclude_value=schema.default, size=1)

    ret = [
        TestCase(
            DELETION_TEST,
            delete_precondition,
            delete,
            delete_setup,
            primitive=True,
        )
    ]
    if schema.enum is not None:
        for case in schema.enum:
            ret.append(EnumTestCase(case, primitive=True))
    else:
        ret.append(
            TestCase(
                PUSH_TEST,
                push_precondition,
                push_mutator,
                push_setup,
                primitive=True,
            )
        )
        ret.append(
            TestCase(
                POP_TEST,
                pop_precondition,
                pop_mutator,
                pop_setup,
                primitive=True,
            )
        )
        ret.append(
            TestCase(
                EMPTY_TEST,
                empty_precondition,
                empty_mutator,
                empty_setup,
                primitive=True,
            )
        )
    return ret


@test_generator(property_type="Boolean", priority=Priority.PRIMITIVE)
def boolean_tests(schema: BooleanSchema):
    """Generate testcases for Boolean type"""
    DELETION_TEST = "boolean-deletion"
    TOGGLE_OFF_TEST = "boolean-toggle-off"
    TOGGLE_ON_TEST = "boolean-toggle-on"

    def toggle_on_precondition(prev):
        if prev is None and schema.default is False:
            return True
        elif prev is False:
            return True
        else:
            return False

    def toggle_on(prev):
        return True

    def toggle_on_setup(prev):
        return False

    def toggle_off_precondition(prev):
        if prev is None and schema.default is True:
            return True
        elif prev is True:
            return True
        else:
            return False

    def toggle_off(prev):
        return False

    def toggle_off_setup(prev):
        return True

    def delete(prev):
        return schema.empty_value()

    def delete_precondition(prev):
        return (
            prev is not None
            and prev != schema.default
            and prev != schema.empty_value()
        )

    def delete_setup(prev):
        logger = get_thread_logger(with_prefix=True)
        if len(schema.examples) > 0:
            logger.info(
                "Using example for setting up field [%s]: [%s]",
                schema.path,
                schema.examples[0],
            )
            example_without_default = [
                x for x in schema.enum if x != schema.default
            ]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return schema.gen(exclude_value=schema.default)
        else:
            return schema.gen(exclude_value=schema.default)

    ret = [
        TestCase(
            DELETION_TEST,
            delete_precondition,
            delete,
            delete_setup,
            primitive=True,
        )
    ]
    if schema.enum is not None:
        for case in schema.enum:
            ret.append(EnumTestCase(case, primitive=True))
    else:
        ret.append(
            TestCase(
                TOGGLE_OFF_TEST,
                toggle_off_precondition,
                toggle_off,
                toggle_off_setup,
                primitive=True,
            )
        )
        ret.append(
            TestCase(
                TOGGLE_ON_TEST,
                toggle_on_precondition,
                toggle_on,
                toggle_on_setup,
                primitive=True,
            )
        )
    return ret


# Commented out because there is no need to support number type yet
# @test_generator(property_type="Number", priority=Priority.PRIMITIVE)
# def number_tests(schema: NumberSchema):
#     """Generate testcases for Number type

#     It handles
#         - minimum
#         - maximum
#         - exclusiveMinimum
#         - exclusiveMaximum
#         - multipleOf
#     """

#     default_minimum = 0
#     default_maximum = 5

#     DELETION_TEST = "number-deletion"
#     INCREASE_TEST = "number-increase"
#     DECREASE_TEST = "number-decrease"
#     EMPTY_TEST = "number-empty"
#     CHANGE_TEST = "number-change"

#     def increase_precondition(prev):
#         if prev is None:
#             return False
#         if schema.multiple_of is None:
#             return prev < schema.maximum
#         else:
#             return prev < schema.maximum - schema.multiple_of

#     def increase(prev):
#         if schema.multiple_of is not None:
#             return prev + schema.multiple_of
#         else:
#             return random.uniform(prev, schema.maximum)

#     def increase_setup(prev):
#         return schema.minimum

#     def decrease_precondition(prev):
#         if prev is None:
#             return False
#         if schema.multiple_of is None:
#             return prev > schema.minimum
#         else:
#             return prev > schema.minimum + schema.multiple_of

#     def decrease(prev):
#         if schema.multiple_of is not None:
#             return prev - schema.multiple_of
#         else:
#             return random.uniform(schema.minimum, prev)

#     def decrease_setup(prev):
#         return schema.maximum

#     def empty_precondition(prev):
#         return prev != 0

#     def empty_mutator(prev):
#         return 0

#     def empty_setup(prev):
#         return 1

#     def change_precondition(prev):
#         return prev is not None

#     def change(prev):
#         """Test case to change the value to another one"""
#         logger = get_thread_logger(with_prefix=True)
#         if schema.enum is not None:
#             logger.fatal(
#                 "Number field with enum should not call change to mutate"
#             )
#         if schema.multiple_of is not None:
#             new_number = random.randrange(
#                 schema.minimum, schema.maximum + 1, schema.multiple_of
#             )
#         else:
#             new_number = random.uniform(schema.minimum, schema.maximum)
#         if prev == new_number:
#             logger.error(
#                 "Failed to change, generated the same number with previous one"
#             )
#         return new_number

#     def change_setup(prev):
#         return 2

#     def delete(prev):
#         return schema.empty_value()

#     def delete_precondition(prev):
#         return (
#             prev is not None
#             and prev != schema.default
#             and prev != schema.empty_value()
#         )

#     def delete_setup(prev):
#         logger = get_thread_logger(with_prefix=True)
#         if len(schema.examples) > 0:
#             logger.info(
#                 "Using example for setting up field [%s]: [%s]",
#                 schema.path,
#                 schema.examples[0],
#             )
#             example_without_default = [
#                 x for x in schema.enum if x != schema.default
#             ]
#             if len(example_without_default) > 0:
#                 return random.choice(example_without_default)
#             else:
#                 return schema.gen(exclude_value=schema.default)
#         else:
#             return schema.gen(exclude_value=schema.default)

#     testcases = [
#         TestCase(DELETION_TEST, delete_precondition, delete, delete_setup)
#     ]
#     if schema.enum is not None:
#         for case in schema.enum:
#             testcases.append(EnumTestCase(case))
#     else:
#         testcases.append(
#             TestCase(CHANGE_TEST, change_precondition, change, change_setup)
#         )
#     return testcases


@test_generator(property_type="Integer", priority=Priority.PRIMITIVE)
def integer_tests(schema: IntegerSchema):
    """Generate testcases for Integer type

    It handles
        - minimum
        - maximum
        - exclusiveMinimum
        - exclusiveMaximum
        - multipleOf
    """
    default_minimum = 0
    default_maximum = 5

    DELETION_TEST = "integer-deletion"
    INCREASE_TEST = "integer-increase"
    DECREASE_TEST = "integer-decrease"
    EMPTY_TEST = "integer-empty"
    CHANGE_TEST = "integer-change"

    def increase_precondition(prev):
        if prev is None:
            return False
        if schema.multiple_of is None:
            return prev < schema.maximum
        else:
            return prev < schema.maximum - schema.multiple_of

    def increase(prev):
        if schema.multiple_of is not None:
            return random.randrange(
                prev, schema.maximum + 1, schema.multiple_of
            )
        else:
            return min(schema.maximum, prev * 2)

    def increase_setup(prev):
        return schema.minimum

    def decrease_precondition(prev):
        if prev is None:
            return False
        if schema.multiple_of is None:
            return prev > schema.minimum
        else:
            return prev > schema.minimum + schema.multiple_of

    def decrease(prev):
        if schema.multiple_of is not None:
            return random.randrange(schema.minimum, prev, schema.multiple_of)
        else:
            return max(schema.minimum, int(prev / 2))

    def decrease_setup(prev):
        return schema.maximum

    def change_precondition(prev):
        return prev is not None

    def change(prev):
        return prev + 2

    def change_setup(prev):
        return 2

    def delete(prev):
        return schema.empty_value()

    def delete_precondition(prev):
        return (
            prev is not None
            and prev != schema.default
            and prev != schema.empty_value()
        )

    def delete_setup(prev):
        logger = get_thread_logger(with_prefix=True)
        if len(schema.examples) > 0:
            logger.info(
                "Using example for setting up field [%s]: [%s]",
                schema.path,
                schema.examples[0],
            )
            example_without_default = [
                x for x in schema.enum if x != schema.default
            ]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return schema.gen(exclude_value=schema.default)
        else:
            return schema.gen(exclude_value=schema.default)

    testcases = [
        TestCase(
            DELETION_TEST,
            delete_precondition,
            delete,
            delete_setup,
            primitive=True,
        )
    ]
    if schema.enum is not None:
        for case in schema.enum:
            testcases.append(EnumTestCase(case))
    else:
        testcases.append(
            TestCase(
                CHANGE_TEST,
                change_precondition,
                change,
                change_setup,
                primitive=True,
            )
        )
    return testcases


@test_generator(property_type="Object", priority=Priority.PRIMITIVE)
def object_tests(schema: ObjectSchema):
    """Generate testcases for Object type

    It handles
        - properties
        - additionalProperties
        - required
        - minProperties
        - maxProperties
    TODO:
        - dependencies
        - patternProperties
        - regexp
    """

    DELETION_TEST = "object-deletion"
    EMPTY_TEST = "object-empty"

    def empty_precondition(prev):
        return prev != {}

    def empty_mutator(prev):
        return {}

    def empty_setup(prev):
        return prev

    def delete(prev):
        return schema.empty_value()

    def delete_precondition(prev):
        return (
            prev is not None
            and prev != schema.default
            and prev != schema.empty_value()
        )

    def delete_setup(prev):
        logger = get_thread_logger(with_prefix=True)
        if len(schema.examples) > 0:
            logger.info(
                "Using example for setting up field [%s]: [%s]",
                schema.path,
                schema.examples[0],
            )
            example_without_default = [
                x for x in schema.enum if x != schema.default
            ]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return schema.gen(exclude_value=schema.default)
        else:
            return schema.gen(exclude_value=schema.default)

    ret = [
        TestCase(
            DELETION_TEST,
            delete_precondition,
            delete,
            delete_setup,
            primitive=True,
        )
    ]
    if schema.enum is not None:
        for case in schema.enum:
            ret.append(EnumTestCase(case))
    else:
        ret.append(
            TestCase(
                EMPTY_TEST,
                empty_precondition,
                empty_mutator,
                empty_setup,
                primitive=True,
            )
        )
    return ret


@test_generator(property_type="Opaque", priority=Priority.PRIMITIVE)
def opaque_gen(schema: OpaqueSchema):
    """Opaque schema to handle the fields that do not have a schema"""
    return []


@test_generator(property_type="String", priority=Priority.PRIMITIVE)
def string_tests(schema: StringSchema):
    """Representation of a generic value generator for string schema

    It handles
        - minLength
        - maxLength
        - pattern
    """
    default_max_length = 10
    DELETION_TEST = "string-deletion"
    CHANGE_TEST = "string-change"
    EMPTY_TEST = "string-empty"

    def change_precondition(prev):
        return prev is not None

    def change(prev):
        """Test case to change the value to another one"""
        logger = get_thread_logger(with_prefix=True)
        if schema.enum is not None:
            logger.fatal(
                "String field with enum should not call change to mutate"
            )
        if schema.pattern is not None:
            new_string = exrex.getone(schema.pattern, schema.max_length)
        else:
            new_string = "ACTOKEY"
        if prev == new_string:
            logger.error(
                "Failed to change, generated the same string with previous one"
            )
        return new_string

    def change_setup(prev):
        logger = get_thread_logger(with_prefix=True)
        if len(schema.examples) > 0:
            logger.info(
                "Using example for setting up field [%s]: [%s]",
                schema.path,
                schema.examples[0],
            )
            return schema.examples[0]
        else:
            return schema.gen()

    def empty_precondition(prev):
        return prev != ""

    def empty_mutator(prev):
        return ""

    def empty_setup(prev):
        return prev

    def delete(prev):
        return schema.empty_value()

    def delete_precondition(prev):
        return (
            prev is not None
            and prev != schema.default
            and prev != schema.empty_value()
        )

    def delete_setup(prev):
        logger = get_thread_logger(with_prefix=True)
        if len(schema.examples) > 0:
            logger.info(
                "Using example for setting up field [%s]: [%s]",
                schema.path,
                schema.examples[0],
            )
            example_without_default = [
                x for x in schema.enum if x != schema.default
            ]
            if len(example_without_default) > 0:
                return random.choice(example_without_default)
            else:
                return schema.gen(exclude_value=schema.default)
        else:
            return schema.gen(exclude_value=schema.default)

    ret = [
        TestCase(
            DELETION_TEST,
            delete_precondition,
            delete,
            delete_setup,
            primitive=True,
        )
    ]
    if schema.enum is not None:
        for case in schema.enum:
            ret.append(EnumTestCase(case, primitive=True))
    else:
        change_testcase = TestCase(
            CHANGE_TEST,
            change_precondition,
            change,
            change_setup,
            primitive=True,
        )
        ret.append(change_testcase)
        ret.append(
            TestCase(
                EMPTY_TEST,
                empty_precondition,
                empty_mutator,
                empty_setup,
                primitive=True,
            )
        )
    return ret


# TODO: Default test generator for Kubernetes schemas
