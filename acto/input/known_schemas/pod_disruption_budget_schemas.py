from acto.schema import BaseSchema, ObjectSchema

from .base import K8sAnyOfSchema, K8sObjectSchema


class LabelSelectorSchema(K8sObjectSchema):

    fields = {
        'matchLabels': K8sObjectSchema,
        'matchExpressions': K8sObjectSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in LabelSelectorSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in LabelSelectorSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True
    
    def __str__(self) -> str:
        return "LabelSelectorSchema"

class PodDisruptionBudgetSpecSchema(K8sObjectSchema):

    fields = {
        'minAvailable': K8sAnyOfSchema,
        'maxUnavailable': K8sAnyOfSchema,
        'selector': K8sObjectSchema
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

    fields = {
        'metadata': K8sObjectSchema,
        'spec': PodDisruptionBudgetSpecSchema
    }

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