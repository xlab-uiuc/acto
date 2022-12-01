from abc import abstractmethod
from typing import List, Tuple
from common import OperatorConfig
from schema import AnyOfSchema, ArraySchema, BaseSchema, BooleanSchema, IntegerSchema, ObjectSchema, StringSchema, extract_schema


class K8sSchema:

    def __init__(self, path: list, schema: dict) -> None:
        super().__init__(path, schema)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj.path, schema_obj.raw_schema)

    @abstractmethod
    def Match(schema) -> bool:
        pass


class K8sStringSchema(K8sSchema, StringSchema):

    def Match(schema: StringSchema) -> bool:
        return isinstance(schema, StringSchema)


class K8sObjectSchema(K8sSchema, ObjectSchema):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, ObjectSchema)


class K8sArraySchema(K8sSchema, ArraySchema):

    def Match(schema: ArraySchema) -> bool:
        return isinstance(schema, ArraySchema)


class K8sIntegerSchema(K8sSchema, IntegerSchema):

    def Match(schema: IntegerSchema) -> bool:
        return isinstance(schema, IntegerSchema)


class K8sBooleanSchema(K8sSchema, BooleanSchema):

    def Match(schema: BooleanSchema) -> bool:
        return isinstance(schema, BooleanSchema)


class K8sAnyOfSchema(K8sSchema, AnyOfSchema):

    def Match(schema: AnyOfSchema) -> bool:
        return isinstance(schema, AnyOfSchema)


class QuantitySchema(K8sAnyOfSchema):

    def Match(schema: AnyOfSchema) -> bool:
        if not K8sAnyOfSchema.Match(schema):
            return False
        for sub_schema in schema.get_possibilities():
            if not isinstance(sub_schema, StringSchema) and not isinstance(
                    sub_schema, IntegerSchema):
                return False

        return True

    def __str__(self) -> str:
        return "Quantity"


class ResourceSchema(K8sObjectSchema):

    additional_properties = QuantitySchema

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        if schema.additional_properties is None:
            return False
        return ResourceSchema.additional_properties.Match(schema.additional_properties)

    def __str__(self) -> str:
        return "Resource"


class ResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": ResourceSchema, "requests": ResourceSchema}

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        if len(schema.properties) != len(ResourceRequirementsSchema.fields):
            return False
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False

        return True

    def __str__(self) -> str:
        return "ResourceRequirements"


class PodManagementPolicySchema(K8sStringSchema):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, StringSchema)

    def __str__(self) -> str:
        return "PodManagementPolicy"


class ReplicasSchema(K8sIntegerSchema):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, IntegerSchema)

    def __str__(self) -> str:
        return "Replicas"


class NodeSelectorSchema(K8sObjectSchema):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, ObjectSchema)

    def __str__(self) -> str:
        return "NodeSelector"


class PreferredSchedulingTermArraySchema(K8sObjectSchema):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, ArraySchema)

    def __str__(self) -> str:
        return "PreferredSchedulingTermArray"


class NodeAffinitySchema(K8sObjectSchema):

    fields = {
        "requiredDuringSchedulingIgnoredDuringExecution": NodeSelectorSchema,
        "preferredDuringSchedulingIgnoredDuringExecution": PreferredSchedulingTermArraySchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in NodeAffinitySchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "NodeAffinity"


class PodAffinityTermArraySchema(K8sArraySchema):

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        return isinstance(schema, ArraySchema)

    def __str__(self) -> str:
        return "PodAffinityTermArray"


class WeightedPodAffinityTermArraySchema(K8sArraySchema):

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        return isinstance(schema, ArraySchema)

    def __str__(self) -> str:
        return "WeightedPodAffinityTermArray"


class PodAffinitySchema(K8sObjectSchema):

    fields = {
        "requiredDuringSchedulingIgnoredDuringExecution": PodAffinityTermArraySchema,
        "preferredDuringSchedulingIgnoredDuringExecution": WeightedPodAffinityTermArraySchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodAffinitySchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PodAffinity"


class PodAntiAffinitySchema(K8sObjectSchema):

    fields = {
        "requiredDuringSchedulingIgnoredDuringExecution": PodAffinityTermArraySchema,
        "preferredDuringSchedulingIgnoredDuringExecution": WeightedPodAffinityTermArraySchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodAntiAffinitySchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PodAntiAffinity"


class AffinitySchema(K8sObjectSchema):

    fields = {
        "nodeAffinity": NodeAffinitySchema,
        "podAffinity": PodAffinitySchema,
        "podAntiAffinity": PodAntiAffinitySchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in AffinitySchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "Affinity"


class PodSecurityContextSchema(K8sObjectSchema):

    fields = {
        "fsGroup": K8sIntegerSchema,
        "runAsGroup": K8sIntegerSchema,
        "runAsNonRoot": K8sBooleanSchema,
        "runAsUser": K8sIntegerSchema,
        "seLinuxOptions": K8sObjectSchema,
        "supplementalGroups": K8sArraySchema,
        "sysctls": K8sArraySchema,
        "windowsOptions": K8sObjectSchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodSecurityContextSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "SecurityContext"


class SecurityContextSchema(K8sObjectSchema):

    fields = {
        "allowPrivilegeEscalation": K8sBooleanSchema,
        "capabilities": K8sObjectSchema,
        "privileged": K8sBooleanSchema,
        "procMount": K8sStringSchema,
        "readOnlyRootFilesystem": K8sBooleanSchema,
        "runAsGroup": K8sIntegerSchema,
        "runAsNonRoot": K8sBooleanSchema,
        "runAsUser": K8sIntegerSchema,
        "seLinuxOptions": K8sObjectSchema,
        "seccompProfile": K8sObjectSchema,
        "windowsOptions": K8sObjectSchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in SecurityContextSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "SecurityContext"


class TolerationSchema(K8sObjectSchema):

    fields = {
        "key": K8sStringSchema,
        "operator": K8sStringSchema,
        "value": K8sStringSchema,
        "effect": K8sStringSchema,
        "tolerationSeconds": K8sIntegerSchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in TolerationSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "Toleration"


class TolerationsSchema(K8sArraySchema):

    item = TolerationSchema

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return TolerationsSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "Tolerations"


class ContainerSchema(K8sObjectSchema):

    fields = {
        "name": K8sStringSchema,
        "image": K8sStringSchema,
        "command": K8sArraySchema,
        "args": K8sArraySchema,
        "workingDir": K8sStringSchema,
        "ports": K8sArraySchema,
        "env": K8sArraySchema,
        "resources": ResourceRequirementsSchema,
        "volumeMounts": K8sArraySchema,
        "livenessProbe": K8sObjectSchema,
        "readinessProbe": K8sObjectSchema,
        "lifecycle": K8sObjectSchema,
        "terminationMessagePath": K8sStringSchema,
        "terminationMessagePolicy": K8sStringSchema,
        "imagePullPolicy": K8sStringSchema,
        "securityContext": SecurityContextSchema,
        "stdin": K8sBooleanSchema,
        "stdinOnce": K8sBooleanSchema,
        "tty": K8sBooleanSchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in ContainerSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "Container"


class ContainersSchema(K8sArraySchema):

    item = ContainerSchema

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return ContainersSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "Containers"


class VolumeSchema(K8sObjectSchema):

    fields = {
        "name": K8sStringSchema,
        "hostPath": K8sObjectSchema,
        "emptyDir": K8sObjectSchema,
        "gcePersistentDisk": K8sObjectSchema,
        "awsElasticBlockStore": K8sObjectSchema,
        "gitRepo": K8sObjectSchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in VolumeSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "Volume"


class VolumesSchema(K8sArraySchema):

    item = VolumeSchema

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return VolumesSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "Volumes"


class TopologySpreadConstraintSchema(K8sObjectSchema):

    fields = {
        "maxSkew": K8sIntegerSchema,
        "topologyKey": K8sStringSchema,
        "whenUnsatisfiable": K8sStringSchema,
        "labelSelector": K8sObjectSchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in TopologySpreadConstraintSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "TopologySpreadConstraint"


class TopologySpreadConstraintsSchema(K8sArraySchema):

    item = TopologySpreadConstraintSchema

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return TopologySpreadConstraintsSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "TopologySpreadConstraint"


class PodSpecSchema(K8sObjectSchema):

    fields = {
        "affinity": AffinitySchema,
        "containers": ContainersSchema,
        "dnsConfig": K8sObjectSchema,
        "dnsPolicy": K8sStringSchema,
        "enableServiceLinks": K8sBooleanSchema,
        "ephemeralContainers": K8sArraySchema,
        "initContainers": ContainersSchema,
        "nodeName": K8sStringSchema,
        "nodeSelector": K8sObjectSchema,
        "preemptionPolicy": K8sStringSchema,
        "priority": K8sIntegerSchema,
        "priorityClassName": K8sStringSchema,
        "restartPolicy": K8sStringSchema,
        "runtimeClassName": K8sStringSchema,
        "schedulerName": K8sStringSchema,
        "securityContext": PodSecurityContextSchema,
        "serviceAccountName": K8sStringSchema,
        "terminationGracePeriodSeconds": K8sIntegerSchema,
        "tolerations": K8sArraySchema,
        "topologySpreadConstraints": K8sArraySchema,
        "volumes": VolumesSchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PodSpec"


class PodTemplateSchema(K8sObjectSchema):

    fields = {
        "metadata": K8sObjectSchema,
        "spec": PodSpecSchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PodTemplateSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PodTemplate"


class StatefulSetSpecSchema(K8sObjectSchema):

    fields = {
        'podManagementPolicy': PodManagementPolicySchema,
        'replicas': ReplicasSchema,
        'selector': K8sObjectSchema,
        'serviceName': K8sStringSchema,
        'template': PodTemplateSchema,
        'updateStrategy': K8sObjectSchema,
        'volumeClaimTemplates': K8sArraySchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in StatefulSetSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "StatefulSetSpecSchema"


class StatefulSetSchema(K8sObjectSchema):

    fields = {"metadata": K8sObjectSchema, "spec": StatefulSetSpecSchema}

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in StatefulSetSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "StatefulSetSchema"


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
        "type": K8sStringSchema
    }

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


class PersistentVolumeClaimSpecSchema(K8sObjectSchema):

    fields = {
        "accessModes": K8sArraySchema,
        "dataSource": K8sObjectSchema,
        "resources": ResourceRequirementsSchema,
        "selector": K8sObjectSchema,
        "storageClassName": K8sStringSchema,
        "volumeMode": K8sStringSchema,
        "volumeName": K8sStringSchema
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PersistentVolumeClaimSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PersistentVolumeClaimSpec"


class PersistentVolumeClaimSchema(K8sObjectSchema):

    fields = {"metadata": K8sObjectSchema, "spec": PersistentVolumeClaimSpecSchema}

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in PersistentVolumeClaimSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "PersistentVolumeClaimSchema"


KUBERNETES_SCHEMA = {
    'statefulSet': StatefulSetSchema,
    'statefulSetSpec': StatefulSetSpecSchema,
    'service': ServiceSchema,
    'serviceSpec': ServiceSpecSchema,
    'affinity': AffinitySchema,
    'securityContext': SecurityContextSchema,
    'podSecurityContextSchema': PodSecurityContextSchema,
    'tolerations': TolerationsSchema,
    'podSpec': PodSpecSchema,
    'template': PodTemplateSchema,
    'container': ContainerSchema,
    'resources': ResourceRequirementsSchema,
    'persistentVolumeClaim': PersistentVolumeClaimSchema,
    'persistentVolumeClaimSpec': PersistentVolumeClaimSpecSchema,
    'volume': VolumeSchema,
    'topologySpreadConstraints': TopologySpreadConstraintsSchema
}


def match_schema(schema: BaseSchema) -> BaseSchema:
    for schema_name, schema_class in KUBERNETES_SCHEMA.items():
        if schema_class.Match(schema):
            return schema_class(schema)
    return None


def find_all_matched_schemas(schema: BaseSchema) -> List[Tuple[BaseSchema, K8sSchema]]:
    matched_schemas = []
    for schema_name, schema_class in KUBERNETES_SCHEMA.items():
        if schema_class.Match(schema):
            matched_schemas.append((schema, schema_class(schema)))
            return matched_schemas
    if isinstance(schema, ObjectSchema):
        for sub_schema in schema.properties.values():
            matched_schemas.extend(find_all_matched_schemas(sub_schema))
    elif isinstance(schema, ArraySchema):
        matched_schemas.extend(find_all_matched_schemas(schema.get_item_schema()))

    return matched_schemas


if __name__ == '__main__':
    import json
    import glob

    for file in glob.glob('data/*/context.json'):
        with open(file, 'r') as f:
            context = json.load(f)
            crd = extract_schema(
                [], context['crd']['body']['spec']['versions'][-1]['schema']['openAPIV3Schema'])
            tuples = find_all_matched_schemas(crd)

            print("Matched schemas for %s:" % file)
            for schema, k8s_schema in tuples:
                print(f"input.CopiedOverField({schema.path}),")