import functools
from typing import Any

from input.value_with_schema import attach_schema_to_value

from acto.input.test_generators.generator import (
    Priority,
    get_testcases,
    test_generator,
)
from acto.input.testcase import TestCase
from acto.schema.under_specified import UnderSpecifiedSchema


@test_generator(property_type="UnderSpecified", priority=Priority.CUSTOM)
def configuration_tests(schema: UnderSpecifiedSchema) -> list[TestCase]:
    """Generate test cases for configuration field"""
    ret = []
    test_cases = get_testcases(schema.underlying_schema, [])

    for path, test_case_list in test_cases:
        for test_case in test_case_list:

            def config_precondition(
                value: Any, config_path: list[str], config_test_case: TestCase
            ) -> bool:
                decoded_value = schema.decode(value)
                value_with_schema = attach_schema_to_value(
                    decoded_value, schema.underlying_schema
                )
                curr_value = value_with_schema.get_value_by_path(config_path)
                return config_test_case.test_precondition(curr_value)

            def config_mutator(
                value: Any, config_path: list[str], config_test_case: TestCase
            ) -> Any:
                decoded_value = schema.decode(value)
                value_with_schema = attach_schema_to_value(
                    decoded_value, schema.underlying_schema
                )
                curr_value = value_with_schema.get_value_by_path(config_path)
                value_with_schema.create_path(config_path)
                new_value = config_test_case.mutator(curr_value)
                value_with_schema.set_value_by_path(config_path, new_value)
                return schema.encode(value_with_schema.raw_value())

            def config_setup(
                value: Any, config_path: list[str], config_test_case: TestCase
            ) -> Any:
                decoded_value = schema.decode(value)
                value_with_schema = attach_schema_to_value(
                    decoded_value, schema.underlying_schema
                )
                new_value = config_test_case.setup(
                    value_with_schema.get_value_by_path(config_path)
                )
                value_with_schema.create_path(config_path)
                value_with_schema.set_value_by_path(config_path, new_value)
                return schema.encode(value_with_schema.raw_value())

            config_test = TestCase(
                name=f"configuration_{path}_{test_case.name}",
                precondition=functools.partial(
                    config_precondition,
                    config_path=path,
                    config_test_case=test_case,
                ),
                mutator=functools.partial(
                    config_mutator,
                    config_path=path,
                    config_test_case=test_case,
                ),
                setup=functools.partial(
                    config_setup,
                    config_path=path,
                    config_test_case=test_case,
                ),
                store=test_case.store,
                primitive=test_case.primitive,
                semantic=test_case.semantic,
                invalid=test_case.invalid,
                kubernetes_schema=test_case.kubernetes_schema,
            )
            ret.append(config_test)
    return ret
