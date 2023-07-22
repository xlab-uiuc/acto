from acto.monkey_patch.monkey_patch import patch_mro

patch_mro('QuantitySchema', ['K8sStringSchema'])

import acto.input.known_schemas
from acto.input.known_schemas import QuantitySchema, K8sObjectSchema, ResourceRequirementsSchema, ResourceSchema, \
    AffinitySchema, K8sStringSchema, K8sBooleanSchema, PriorityClassNameSchema, PodSecurityContextSchema, \
    K8sIntegerSchema, TolerationsSchema, TopologySpreadConstraintsSchema, PodDisruptionBudgetSpecSchema
from acto.monkey_patch.monkey_patch import MonkeyPatchSupportMetaClass
from acto.schema import ObjectSchema, BaseSchema


def MatchResourceSchema(schema: ObjectSchema) -> bool:
    if not K8sObjectSchema.Match(schema):
        return False
    return 'x-kubernetes-preserve-unknown-fields' in schema.raw_schema and schema.raw_schema['x-kubernetes-preserve-unknown-fields']


def InitResourceSchema(self, schema_obj: BaseSchema):
    super(ResourceSchema, self).__init__(schema_obj)
    self.additional_properties = QuantitySchema(schema_obj)


MonkeyPatchSupportMetaClass.override_class_attrs['ResourceSchema'] = {
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


MonkeyPatchSupportMetaClass.override_class_attrs['ResourceRequirementsSchema'] = {
    'Match': MatchResourceRequirementsSchema
}

MonkeyPatchSupportMetaClass.override_class_attrs['PodSpecSchema'] = {
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

# here is an example to add a extra class to the default KUBERNETES_SCHEMA
# the following line won't take effect because of the schema difference
acto.input.known_schemas.KUBERNETES_SCHEMA['podDisruptionBudget'] = PodDisruptionBudgetSpecSchema
# Strimzi-kafka operator has deployment field, but it can be handled automatically by enum
# because the schema is very simple
"""
deployment:
  type: object
  properties:
    metadata:
      type: object
      properties:
        labels:
          x-kubernetes-preserve-unknown-fields: true
          type: object
          description: Labels added to the Kubernetes resource.
        annotations:
          x-kubernetes-preserve-unknown-fields: true
          type: object
          description: >-
            Annotations added to the Kubernetes
            resource.
      description: Metadata applied to the resource.
    deploymentStrategy:
      type: string
      enum:
        - RollingUpdate
        - Recreate
      description: >-
        Pod replacement strategy for deployment
        configuration changes. Valid values are
        `RollingUpdate` and `Recreate`. Defaults to
        `RollingUpdate`.
  description: Template for Cruise Control `Deployment`.
"""

# Strimzi-kafka operator has stateful set field, but it can be handled automatically by enum
# because the schema is very simple
"""
statefulset:
  type: object
  properties:
    metadata:
      type: object
      properties:
        labels:
          x-kubernetes-preserve-unknown-fields: true
          type: object
          description: Labels added to the Kubernetes resource.
        annotations:
          x-kubernetes-preserve-unknown-fields: true
          type: object
          description: >-
            Annotations added to the Kubernetes
            resource.
      description: Metadata applied to the resource.
    podManagementPolicy:
      type: string
      enum:
        - OrderedReady
        - Parallel
      description: >-
        PodManagementPolicy which will be used for this
        StatefulSet. Valid values are `Parallel` and
        `OrderedReady`. Defaults to `Parallel`.
  description: Template for ZooKeeper `StatefulSet`.
"""
