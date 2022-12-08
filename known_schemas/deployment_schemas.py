from typing import List, Tuple
from schema import BaseSchema, ObjectSchema
from known_schemas.base import K8sBooleanSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema
from known_schemas.pod_schemas import PodSpecSchema
from known_schemas.statefulset_schemas import PodManagementPolicySchema, ReplicasSchema, PodTemplateSchema
from schema import BaseSchema

class DeploymentSpecSchema(K8sObjectSchema):

    fields = {
        "minReadySeconds": K8sIntegerSchema,
        "paused": K8sBooleanSchema,
        "progressDeadlineSeconds": K8sIntegerSchema,
        "replicas": ReplicasSchema,
        "revisionHistoryLimit": K8sIntegerSchema,
        "selector": K8sObjectSchema,
        "strategy": K8sObjectSchema,
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
