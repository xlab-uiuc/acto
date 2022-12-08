from typing import List, Tuple
from schema import BaseSchema, ObjectSchema
from known_schemas.base import K8sBooleanSchema, K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema
from test_case import TestCase

class ServiceTypeSchema(K8sStringSchema):

    def service_type_change_precondition(prev):
        return prev is not None

    def service_type_change(prev):
        if prev == 'ClusterIP':
            return 'NodePort'
        else:
            return 'ClusterIP'

    def service_type_change_setup(prev):
        return 'ClusterIP'

    ServiceTypeChangeTestcase = TestCase(service_type_change_precondition, service_type_change,
                                         service_type_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'LoadBalancer':
            return 'ClusterIP'
        else:
            return 'LoadBalancer'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ServiceTypeSchema.ServiceTypeChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ServiceType"


class ServiceSpecSchema(K8sObjectSchema):

    fields = {
        "allocateLoadBalancerNodePorts": K8sBooleanSchema,
        "clusterIP": K8sStringSchema,
        "clusterIPs": K8sArraySchema,
        "externalIPs": K8sArraySchema,
        "externalName": K8sStringSchema,
        "externalTrafficPolicy": K8sStringSchema,
        "healthCheckNodePort": K8sIntegerSchema,
        "ipFamilies": K8sArraySchema,
        "loadBalancerIP": K8sStringSchema,
        "loadBalancerSourceRanges": K8sArraySchema,
        "ports": K8sArraySchema,
        "publishNotReadyAddresses": K8sBooleanSchema,
        "selector": K8sObjectSchema,
        "sessionAffinity": K8sStringSchema,
        "sessionAffinityConfig": K8sObjectSchema,
        "topologyKeys": K8sArraySchema,
        "type": ServiceTypeSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ServiceSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in ServiceSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "ServiceSpecSchema"


class ServiceSchema(K8sObjectSchema):

    fields = {"metadata": K8sObjectSchema, "spec": ServiceSpecSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ServiceSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in ServiceSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "ServiceSchema"
