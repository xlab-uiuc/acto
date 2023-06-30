from acto.input.known_schemas import QuantitySchema, K8sStringSchema, K8sObjectSchema, ResourceRequirementsSchema
from acto.monkey_patch.monkey_patch import MonkeyPatchSupportMetaClass, patch_mro
from acto.schema import ObjectSchema

# Monkey patch for QuantitySchema

patch_mro(QuantitySchema, type('QuantitySchema', (K8sStringSchema,), {}))

def MatchResourceSchema(schema: ObjectSchema) -> bool:
    if not K8sObjectSchema.Match(schema):
        return False
    return 'x-kubernetes-preserve-unknown-fields' in schema.raw_schema and schema.raw_schema['x-kubernetes-preserve-unknown-fields']


MonkeyPatchSupportMetaClass.override_class_methods['ResourceSchema'] = {
    'Match': MatchResourceSchema
}


def MatchResourceRequirementsSchema(schema: ObjectSchema) -> bool:
    if not K8sObjectSchema.Match(schema):
        return False
    if len(schema.properties) < len(ResourceRequirementsSchema.fields):
        return False
    for field, field_schema in ResourceRequirementsSchema.fields.items():
        if field not in schema.properties:
            return False
        elif not field_schema.Match(schema.properties[field]):
            return False

    return True

MonkeyPatchSupportMetaClass.override_class_methods['ResourceRequirementsSchema'] = {
    'Match': MatchResourceRequirementsSchema
}
