from typing import List, Tuple
from schema import BaseSchema, IntegerSchema, ObjectSchema
from known_schemas.base import K8sBooleanSchema, K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema
from test_case import TestCase, K8sTestCase

class PortSchema(K8sIntegerSchema):

    def port_privilege_precondition(prev):
        return prev == 26257
    
    def port_privilege(prev):
        return 8888
    
    def port_privilege_setup(prev):
        return 26257

    PortPrivilegeTestcase = K8sTestCase(port_privilege_precondition, port_privilege, port_privilege_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == None:
            return 26257
        elif exclude_value == 26257:
            return 26258
        else:
            return 26257

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, IntegerSchema)

    def __str__(self) -> str:
        return "Port"

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

    ServiceTypeChangeTestcase = K8sTestCase(service_type_change_precondition, service_type_change,
                                         service_type_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'LoadBalancer':
            return 'ClusterIP'
        else:
            return 'LoadBalancer'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ServiceTypeSchema.ServiceTypeChangeTestcase])
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ServiceType"
    

class ExternalTrafficPolicySchema(K8sStringSchema):

    def external_traffic_policy_change_precondition(prev):
        return prev is not None

    def external_traffic_policy_change(prev):
        if prev == 'Cluster':
            return 'Local'
        else:
            return 'Cluster'

    def external_traffic_policy_change_setup(prev):
        return 'Cluster'

    ExternalTrafficPolicyChangeTestcase = K8sTestCase(external_traffic_policy_change_precondition, external_traffic_policy_change,
                                         external_traffic_policy_change_setup)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.default = 'Cluster'

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'Local':
            return 'Cluster'
        else:
            return 'Local'

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ExternalTrafficPolicy"
    

class IpRangeSchema(K8sStringSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)
    
    def __str__(self) -> str:
        return "IpRange"
    

class LoadBalancerSourceRangesSchema(K8sArraySchema):

    item = IpRangeSchema

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.item_schema = LoadBalancerSourceRangesSchema.item(schema_obj.item_schema)

    def Match(schema: ObjectSchema) -> bool:
        return K8sArraySchema.Match(schema) and IpRangeSchema.Match(schema.items)
    
    def __str__(self) -> str:
        return "LoadBalancerSourceRanges"


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
        "loadBalancerSourceRanges": LoadBalancerSourceRangesSchema,
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
    
class IngressTLSSchema(K8sObjectSchema):

    def non_existent_secret_precondition(prev):
        return True

    def non_existent_secret(prev):
        return {
            "hosts": ["test.com"],
            "secretName": "non-existent-secret"
        }

    def non_existent_secret_setup(prev):
        return None

    NonExistentSecretTestcase = K8sTestCase(non_existent_secret_precondition, non_existent_secret, non_existent_secret_setup)

    fields = {
        "hosts": K8sArraySchema,
        "secretName": K8sStringSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in IngressTLSSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])
    
    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in IngressTLSSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([IngressTLSSchema.NonExistentSecretTestcase])
        return base_testcases
    
    def __str__(self) -> str:
        return "IngressTLSSchema"