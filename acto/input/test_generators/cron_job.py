# pylint: disable=unused-argument
from acto.input.test_generators.generator import generator
from acto.input.testcase import TestCase
from acto.schema.object import ObjectSchema
from acto.schema.string import StringSchema


@generator(field_name="concurrentPolicy")
def concurrent_policy_tests(schema: StringSchema) -> list[TestCase]:
    """Generate test cases for concurrentPolicy field"""
    invalid_test = TestCase(
        "invalid-concurrentPolicy",
        lambda x: True,
        lambda x: "InvalidConcurrencyPolicy",
        lambda x: "Forbid",
    )
    change_test = TestCase(
        "concurrentPolicy-change",
        lambda x: True,
        lambda x: "Forbid" if x == "Replace" else "Replace",
        lambda x: "Forbid",
    )
    return [invalid_test, change_test]


@generator(field_name="schedule")
def schedule_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for schedule field"""
    invalid_test = TestCase(
        "invalid-schedule",
        lambda x: True,
        lambda x: "InvalidSchedule",
        lambda x: "0 * * * *",
    )
    change_test = TestCase(
        "schedule-change",
        lambda x: True,
        lambda x: "0 * * * *" if x == "1 * * * *" else "1 * * * *",
        lambda x: "0 * * * *",
    )
    return [invalid_test, change_test]
