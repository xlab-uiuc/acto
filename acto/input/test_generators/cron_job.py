# pylint: disable=unused-argument
from acto.input.test_generators.generator import Priority, test_generator
from acto.input.testcase import TestCase
from acto.schema.string import StringSchema


@test_generator(property_name="concurrentPolicy", priority=Priority.SEMANTIC)
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


@test_generator(property_name="schedule", priority=Priority.SEMANTIC)
def schedule_tests(schema: StringSchema) -> list[TestCase]:
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
