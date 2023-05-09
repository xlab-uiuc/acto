from typing import List, Tuple
from acto.schema import AnyOfSchema, ArraySchema, BaseSchema, BooleanSchema, IntegerSchema, ObjectSchema, StringSchema, extract_schema
from acto.input.testcase import TestCase, K8sTestCase

from .base import K8sSchema, K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema, K8sBooleanSchema, K8sAnyOfSchema
from .statefulset_schemas import StatefulSetSchema, StatefulSetSpecSchema, PodTemplateSchema
from .deployment_schemas import DeploymentSchema, DeploymentSpecSchema
from .service_schemas import ServiceSchema, ServiceSpecSchema
from .pod_disruption_budget_schemas import PodDisruptionBudgetSchema
from .pod_schemas import AffinitySchema, PodSpecSchema, ContainerSchema, ResourceRequirementsSchema, SecurityContextSchema, PodSecurityContextSchema, TolerationsSchema, VolumeSchema, TopologySpreadConstraintsSchema
from .resource_schemas import ResourceRequirementsSchema
from .storage_schemas import PersistentVolumeClaimSchema, PersistentVolumeClaimSpecSchema


class NodeNameSchema(K8sStringSchema):

    def node_name_change_precondition(prev):
        return prev is not None

    def node_name_change(prev):
        if prev == 'kind-worker':
            return 'kind-worker1'
        else:
            return 'kind-worker'

    def node_name_change_setup(prev):
        return 'kind-worker'

    NodeNameChangeTestcase = K8sTestCase(node_name_change_precondition, node_name_change,
                                         node_name_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return "kind-worker"

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([NodeNameSchema.NodeNameChangeTestcase])
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "NodeName"


KUBERNETES_SCHEMA = {
    'statefulSet': StatefulSetSchema,
    'statefulSetSpec': StatefulSetSpecSchema,
    'deployment': DeploymentSchema,
    'deploymentSpec': DeploymentSpecSchema,
    'service': ServiceSchema,
    'serviceSpec': ServiceSpecSchema,
    'affinity': AffinitySchema,
    'securityContext': SecurityContextSchema,
    'podSecurityContextSchema': PodSecurityContextSchema,
    'podDisruptionBudget': PodDisruptionBudgetSchema,
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

    files = glob.glob('data/*/context.json')
    files.sort()
    for file in files:
        with open(file, 'r') as f:
            context = json.load(f)
            crd = extract_schema(
                [], context['crd']['body']['spec']['versions'][-1]['schema']['openAPIV3Schema'])
            tuples = find_all_matched_schemas(crd)

            print("Matched schemas for %s:" % file)
            for schema, k8s_schema in tuples:
                print(
                    f"known_schemas.K8sField({schema.path}, known_schemas.{type(k8s_schema).__name__}),"
                )

            print()