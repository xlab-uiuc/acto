# pylint: disable=unused-argument
from acto.input.test_generators.generator import generator
from acto.input.testcase import TestCase
from acto.schema.object import ObjectSchema
from acto.schema.string import StringSchema


@generator(property_name="concurrentPolicy")
def concurrent_policy_tests(schema: StringSchema) -> list[TestCase]:
    """Generate test cases for concurrentPolicy field"""
    invalid_test = TestCase(
        "k8s-invalid_concurrency_policy_change",
        lambda x: True,
        lambda x: "InvalidConcurrencyPolicy",
        lambda x: "Forbid",
        invalid=True,
        semantic=True,
    )
    change_test = TestCase(
        "k8s-concurrency_policy_change",
        lambda x: True,
        lambda x: "Forbid" if x == "Replace" else "Replace",
        lambda x: "Forbid",
        semantic=True,
    )
    return [invalid_test, change_test]


@generator(property_name="schedule")
def schedule_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for schedule field"""
    invalid_test = TestCase(
        "k8s-invalid_cronjob_schedule_change",
        lambda x: True,
        lambda x: "InvalidSchedule",
        lambda x: "0 * * * *",
        invalid=True,
        semantic=True,
    )
    change_test = TestCase(
        "k8s-cronjob_schedule_change",
        lambda x: True,
        lambda x: "0 * * * *" if x == "1 * * * *" else "1 * * * *",
        lambda x: "0 * * * *",
        semantic=True,
    )
    return [invalid_test, change_test]
