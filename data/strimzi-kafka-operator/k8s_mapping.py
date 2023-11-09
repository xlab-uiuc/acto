from acto.input.known_schemas import QuantitySchema, K8sObjectSchema, ResourceRequirementsSchema, ResourceSchema, AffinitySchema, K8sStringSchema, K8sBooleanSchema, PriorityClassNameSchema, PodSecurityContextSchema, K8sIntegerSchema, TolerationsSchema, TopologySpreadConstraintsSchema
from acto.monkey_patch.monkey_patch import MonkeyPatchSupportMetaClass
from acto.schema import ObjectSchema, BaseSchema


def MatchResourceSchema(schema: ObjectSchema) -> bool:
    if not K8sObjectSchema.Match(schema):
        return False
    return 'x-kubernetes-preserve-unknown-fields' in schema.raw_schema and schema.raw_schema['x-kubernetes-preserve-unknown-fields']


def InitResourceSchema(self, schema_obj: BaseSchema):
    super(ResourceSchema, self).__init__(schema_obj)
    self.additional_properties = QuantitySchema(schema_obj)


MonkeyPatchSupportMetaClass.override_class_methods['ResourceSchema'] = {
    'Match': MatchResourceSchema,
    '__init__': InitResourceSchema
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

MonkeyPatchSupportMetaClass.override_class_methods['PodSpecSchema'] = {
    'fields': {
        "metadata": K8sObjectSchema,
        "affinity": AffinitySchema,
        "enableServiceLinks": K8sBooleanSchema,
        "schedulerName": K8sStringSchema,
        "priorityClassName": PriorityClassNameSchema,
        # "hostAliases": ,
        # "tmpDirSizeLimit": ,
        "securityContext": PodSecurityContextSchema,
        "terminationGracePeriodSeconds": K8sIntegerSchema,
        "tolerations": TolerationsSchema,
        "topologySpreadConstraints": TopologySpreadConstraintsSchema,
    }
}
