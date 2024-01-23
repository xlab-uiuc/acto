# pylint: disable=unused-argument
from acto.input.test_generators.generator import generator
from acto.input.testcase import TestCase
from acto.schema.object import ObjectSchema

# XXX: Need to solve
# @generator(field_name="type", paths=[""])
# def service_type_tests(schema: ObjectSchema) -> list[TestCase]:
#     """Generate test cases for serviceType field"""
#     invalid_test = TestCase(
#         "invalid-serviceType",
#         lambda x: True,
#         lambda x: "InvalidServiceType",
#         lambda x: "ClusterIP",
#     )
#     change_test = TestCase(
#         "serviceType-change",
#         lambda x: x != "NodePort",
#         lambda x: "NodePort",
#         lambda x: "ClusterIP",
#     )
#     return [invalid_test, change_test]


@generator(k8s_schema_name="networking.v1.IngressTLS")
def ingress_tls_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for ingressTLS field"""
    invalid_test = TestCase(
        "k8s-non_existent_secret",
        lambda x: True,
        lambda x: {"hosts": ["test.com"], "secretName": "non-existent"},
        lambda x: None,
    )
    change_test = TestCase(
        "k8s-ingressTLS-change",
        lambda x: x != {"hosts": ["example.com"]},
        lambda x: {"hosts": ["example.com"]},
        lambda x: {"hosts": ["example.org"]},
    )
    return [invalid_test, change_test]
