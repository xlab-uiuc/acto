# pylint: disable=unused-argument
from acto.input.test_generators.generator import Priority, test_generator
from acto.input.testcase import TestCase
from acto.schema.array import ArraySchema
from acto.schema.string import StringSchema


@test_generator(property_name="accessModes", priority=Priority.SEMANTIC)
def access_mode_tests(schema: ArraySchema) -> list[TestCase]:
    """Generate test cases for accessModes field"""
    invalid_test = TestCase(
        "k8s-invalid_access_mode",
        lambda x: True,
        lambda x: ["InvalidAccessMode"],
        lambda x: ["ReadWriteOnce"],
        invalid=True,
        semantic=True,
    )
    change_test = TestCase(
        "k8s-change_access_mode",
        lambda x: True,
        lambda x: ["ReadWriteOnce"]
        if x == ["ReadWriteMany"]
        else ["ReadWriteMany"],
        lambda x: ["ReadWriteOnce"],
        semantic=True,
    )
    return [invalid_test, change_test]


@test_generator(property_name="apiVersion", priority=Priority.SEMANTIC)
def api_version_tests(schema: StringSchema) -> list[TestCase]:
    """Generate test cases for apiVersion field"""
    change_test = TestCase(
        "k8s-change_api_version",
        lambda x: True,
        lambda x: "v1" if x == "v2" else "v2",
        lambda x: "v1",
        semantic=True,
    )
    return [change_test]
