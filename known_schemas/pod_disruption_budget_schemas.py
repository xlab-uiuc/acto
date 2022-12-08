from typing import List, Tuple
from schema import BaseSchema, ObjectSchema
from known_schemas.base import K8sObjectSchema, K8sIntegerSchema
from test_case import TestCase

class PodDisruptionBudgetSpecSchema(K8sObjectSchema):

    fields = {
        "maxUnavailable": K8sIntegerSchema,
        "minAvailable": K8sIntegerSchema,
        "selector": K8sObjectSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodDisruptionBudgetSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodDisruptionBudgetSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PodDisruptionBudgetSpecSchema"


class PodDisruptionBudgetSchema(K8sObjectSchema):

    fields = {"metadata": K8sObjectSchema, "spec": K8sObjectSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodDisruptionBudgetSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodDisruptionBudgetSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PodDisruptionBudgetSchema"
