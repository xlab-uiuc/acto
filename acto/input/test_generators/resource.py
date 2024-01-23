# pylint: disable=unused-argument
from acto.input.test_generators.generator import test_generator
from acto.input.testcase import TestCase
from acto.k8s_util.k8sutil import (
    canonicalize_quantity,
    double_quantity,
    half_quantity,
)
from acto.schema.object import ObjectSchema
from acto.schema.string import StringSchema


@test_generator(k8s_schema_name="apimachinery.pkg.api.resource.Quantity")
def quantity_tests(schema: StringSchema) -> list[TestCase]:
    """Generate test cases for quantity field"""
    increase_test = TestCase(
        "k8s-quantity_increase",
        lambda x: x is not None and canonicalize_quantity(x) != "INVALID",
        double_quantity,
        lambda x: "2000m",
    )
    decrease_test = TestCase(
        "k8s-quantity_decrease",
        lambda x: x is not None and canonicalize_quantity(x) != "INVALID",
        half_quantity,
        lambda x: "1000m",
    )
    return [increase_test, decrease_test]


@test_generator(k8s_schema_name="core.v1.ResourceRequirements")
def resource_requirements_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for resourceRequirements field"""
    invalid_test = TestCase(
        "invalid-resourceRequirements",
        lambda x: True,
        lambda x: {"limits": {"hugepages-2Mi": "1000m"}},
        lambda x: None,
        invalid=True,
        semantic=True,
    )
    change_test = TestCase(
        "resourceRequirements-change",
        lambda x: x != {"limits": {"cpu": "1000m"}},
        lambda x: {"limits": {"cpu": "1000m"}},
        lambda x: {"limits": {"cpu": "2000m"}},
        semantic=True,
    )
    return [invalid_test, change_test]


@test_generator(k8s_schema_name="core.v1.VolumeResourceRequirements")
def volume_resource_requirements_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for volumeResourceRequirements field"""
    invalid_test = TestCase(
        "k8s-invalid-volumeResourceRequirements",
        lambda x: True,
        lambda x: {"request": {"INVALID": "1000m"}},
        lambda x: None,
        invalid=True,
        semantic=True,
    )
    change_test = TestCase(
        "k8s-volumeResourceRequirements-change",
        lambda x: x != {"request": {"storage": "1000Mi"}},
        lambda x: {"request": {"storage": "1000Mi"}},
        lambda x: {"request": {"storage": "2000Mi"}},
        semantic=True,
    )
    return [invalid_test, change_test]
