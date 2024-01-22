# pylint: disable=unused-argument
from acto.input.test_generators.generator import generator
from acto.input.testcase import TestCase
from acto.schema.object import ObjectSchema


@generator(k8s_schema_name="apps.v1.DeploymentStrategy")
def deployment_strategy_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for deploymentStrategy field"""
    invalid_test = TestCase(
        "invalid-deploymentStrategy",
        lambda x: True,
        lambda x: {"type": "INVALID_DEPLOYMENT_STRATEGY"},
        lambda x: None,
    )
    change_test = TestCase(
        "deploymentStrategy-change",
        lambda x: x != {"type": "RollingUpdate"},
        lambda x: {"type": "RollingUpdate"},
        lambda x: {"type": "Recreate"},
    )
    return [invalid_test, change_test]
