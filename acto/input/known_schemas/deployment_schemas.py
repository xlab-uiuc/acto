
from typing import List, Tuple

from acto.input.testcase import K8sInvalidTestCase, TestCase
from acto.schema import BaseSchema, ObjectSchema, StringSchema

from .base import (K8sArraySchema, K8sBooleanSchema, K8sIntegerSchema,
                   K8sObjectSchema, K8sStringSchema)
from .statefulset_schemas import (PodManagementPolicySchema, PodTemplateSchema,
                                  ReplicasSchema)


class DeploymentStrategy(K8sStringSchema):

    def invalid_deployment_strategy(prev):
        return "INVALID_DEPLOYMENT_STRATEGY"
    
    InvalidDeploymentStrategy = K8sInvalidTestCase(lambda prev: prev is not None,
                                            invalid_deployment_strategy, lambda prev: "RollingUpdate")
    
    def gen(self, exclude_value=None, **kwargs):
        if exclude_value == None:
            return "RollingUpdate"
        elif exclude_value == "RollingUpdate":
            return "Recreate"
        else:
            return "RollingUpdate"
        
    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_cases = super().test_cases()
        base_cases[1].append(DeploymentStrategy.InvalidDeploymentStrategy)
        return base_cases

    def Match(schema: StringSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "DeploymentStrategy"

class DeploymentSpecSchema(K8sObjectSchema):

    fields = {
        "minReadySeconds": K8sIntegerSchema,
        "paused": K8sBooleanSchema,
        "progressDeadlineSeconds": K8sIntegerSchema,
        "replicas": ReplicasSchema,
        "revisionHistoryLimit": K8sIntegerSchema,
        "selector": K8sObjectSchema,
        "strategy": DeploymentStrategy,
        "template": PodTemplateSchema,
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in DeploymentSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in DeploymentSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "DeploymentSpecSchema"


class DeploymentSchema(K8sObjectSchema):

    fields = {"metadata": K8sObjectSchema, "spec": DeploymentSpecSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in DeploymentSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in DeploymentSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "DeploymentSchema"
