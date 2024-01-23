# pylint: disable=unused-argument
from acto.input.test_generators.generator import test_generator
from acto.input.testcase import TestCase
from acto.schema.object import ObjectSchema


@test_generator(k8s_schema_name="apps.v1.DeploymentStrategy")
def deployment_strategy_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for deploymentStrategy field"""
    invalid_test = TestCase(
        "k8s-invalid_deployment_strategy",
        lambda x: True,
        lambda x: {"type": "INVALID_DEPLOYMENT_STRATEGY"},
        lambda x: None,
        invalid=True,
        semantic=True,
    )
    change_test = TestCase(
        "k8s-deployment_strategy_change",
        lambda x: x != {"type": "RollingUpdate"},
        lambda x: {"type": "RollingUpdate"},
        lambda x: {"type": "Recreate"},
        semantic=True,
    )
    return [invalid_test, change_test]
