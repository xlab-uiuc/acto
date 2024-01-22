# pylint: disable=unused-argument
from acto.input.test_generators.generator import generator
from acto.input.testcase import TestCase
from acto.schema.array import ArraySchema
from acto.schema.string import StringSchema


@generator(field_name="accessModes")
def access_mode_tests(schema: ArraySchema) -> list[TestCase]:
    """Generate test cases for accessModes field"""
    invalid_test = TestCase(
        "invalid-accessModes",
        lambda x: True,
        lambda x: ["InvalidAccessMode"],
        lambda x: ["ReadWriteOnce"],
    )
    change_test = TestCase(
        "accessModes-change",
        lambda x: True,
        lambda x: ["ReadWriteOnce"]
        if x == ["ReadWriteMany"]
        else ["ReadWriteMany"],
        lambda x: ["ReadWriteOnce"],
    )
    return [invalid_test, change_test]


@generator(field_name="apiVersion")
def api_version_tests(schema: StringSchema) -> list[TestCase]:
    """Generate test cases for apiVersion field"""
    change_test = TestCase(
        "apiVersion-change",
        lambda x: True,
        lambda x: "v1" if x == "v2" else "v2",
        lambda x: "v1",
    )
    return [change_test]
