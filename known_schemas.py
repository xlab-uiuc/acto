from abc import abstractmethod
from typing import List, Tuple
from k8s_util.k8sutil import canonicalizeQuantity, double_quantity, half_quantity
from schema import AnyOfSchema, ArraySchema, BaseSchema, BooleanSchema, IntegerSchema, ObjectSchema, StringSchema, extract_schema
from test_case import TestCase


class K8sField():

    def __init__(self, path, schema) -> None:
        self.path = path
        self.custom_schema = schema


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

    def increase_precondition(prev) -> bool:
        if prev == None:
            return False
        elif canonicalizeQuantity(prev) == 'INVALID':
            return False
        return True

    def increase(prev):
        return double_quantity(prev)

    def increase_setup(prev):
        return "1000m"

    def decrease_precondition(prev) -> bool:
        if prev == None:
            return False
        elif canonicalizeQuantity(prev) == 'INVALID':
            return False
        return True

    def decrease(prev):
        return half_quantity(prev)

    def decrease_setup(prev):
        return "1000m"

    Increase = TestCase(increase_precondition, increase, increase_setup)
    Decrease = TestCase(decrease_precondition, decrease, decrease_setup)

    def Match(schema: AnyOfSchema) -> bool:
        if not K8sAnyOfSchema.Match(schema):
            return False
        for sub_schema in schema.get_possibilities():
            if not isinstance(sub_schema, StringSchema) and not isinstance(
                    sub_schema, IntegerSchema):
                return False

        return True

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return '1000m'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_test_cases = super().test_cases()
        base_test_cases[1].extend([QuantitySchema.Increase, QuantitySchema.Decrease])
        return base_test_cases

    def __str__(self) -> str:
        return "Quantity"


class ResourceSchema(K8sObjectSchema):

    additional_properties = QuantitySchema

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.additional_properties = ResourceSchema.additional_properties(
            self.additional_properties)

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        if schema.additional_properties is None:
            return False
        return ResourceSchema.additional_properties.Match(schema.additional_properties)

    def __str__(self) -> str:
        return "Resource"


class ComputeResourceSchema(ResourceSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.properties['cpu'] = QuantitySchema(self.additional_properties)
        self.properties['memory'] = QuantitySchema(self.additional_properties)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return {'cpu': '1000m', 'memory': '1000m'}


class StorageResourceSchema(ResourceSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.properties['storage'] = QuantitySchema(self.additional_properties)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return {'storage': '1000m'}

    def __str__(self) -> str:
        return "StorageResource"


class ComputeResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": ComputeResourceSchema, "requests": ComputeResourceSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ComputeResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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


class StorageResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": StorageResourceSchema, "requests": StorageResourceSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in StorageResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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


class ResourceRequirementsSchema(K8sObjectSchema):

    fields = {"limits": ResourceSchema, "requests": ResourceSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ResourceRequirementsSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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
    '''ScaleDownUp and ScaleUpDown'''

    def scaleDownUpPrecondition(prev) -> bool:
        return False

    def scaleDownUp(prev) -> int:
        return prev + 1

    def scaleDownUpSetup(prev) -> int:
        if prev == None:
            return 1
        return prev - 1

    def scaleUpDownPrecondition(prev) -> bool:
        return False

    def scaleUpDown(prev) -> int:
        return prev + 1

    def scaleUpDownSetup(prev) -> int:
        if prev == None:
            return 4
        return prev + 1

    ScaleDownUp = TestCase(scaleDownUpPrecondition, scaleDownUp, scaleDownUpSetup)
    ScaleUpDown = TestCase(scaleUpDownPrecondition, scaleUpDown, scaleUpDownSetup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        if exclude_value is None:
            return 3
        else:
            return exclude_value + 1

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, IntegerSchema)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ReplicasSchema.ScaleDownUp, ReplicasSchema.ScaleUpDown])
        return base_testcases

    def __str__(self) -> str:
        return "Replicas"


class NodeSelectorSchema(K8sObjectSchema):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, ObjectSchema)

    def __str__(self) -> str:
        return "NodeSelector"


class PreferredSchedulingTermArraySchema(K8sArraySchema):

    def Match(schema: ObjectSchema) -> bool:
        return isinstance(schema, ArraySchema)

    def __str__(self) -> str:
        return "PreferredSchedulingTermArray"


class NodeAffinitySchema(K8sObjectSchema):

    fields = {
        "requiredDuringSchedulingIgnoredDuringExecution": NodeSelectorSchema,
        "preferredDuringSchedulingIgnoredDuringExecution": PreferredSchedulingTermArraySchema
    }

    OneNodeAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [{
                "matchExpressions": [{
                    "key": "kubernetes.io/hostname",
                    "operator": "In",
                    "values": ["kind-worker",]
                }]
            }]
        }
    }

    PlainNodeAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [{
                "matchExpressions": [{
                    "key": "kubernetes.io/hostname",
                    "operator": "In",
                    "values": [
                        "kind-worker",
                        "kind-worker2",
                        "kind-worker3"
                        "kind-control-plane",
                    ]
                }]
            }]
        }
    }

    UnAchievableNodeAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [{
                "matchExpressions": [{
                    "key": "kubernetes.io/hostname",
                    "operator": "In",
                    "values": ["NULL",]
                }]
            }]
        }
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in NodeAffinitySchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    AllOnOneNodeAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": [{
            "labelSelector": {
                "matchExpressions": [{
                    "key": "app.kubernetes.io/name",
                    "operator": "In",
                    "values": ["test-cluster"]
                }]
            },
            "topologyKey": "kubernetes.io/hostname"
        }]
    }

    PlainPodAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": [{
            "labelSelector": {
                "matchExpressions": [{
                    "key": "app.kubernetes.io/name",
                    "operator": "In",
                    "values": ["test-cluster"]
                }]
            },
            "topologyKey": "kubernetes.io/os"
        }]
    }

    UnAchievablePodAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": [{
            "labelSelector": {
                "matchExpressions": [{
                    "key": "app.kubernetes.io/name",
                    "operator": "In",
                    "values": ["test-cluster"]
                }]
            },
            "topologyKey": "NULL"
        }]
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodAffinitySchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return PodAffinitySchema.AllOnOneNodeAffinity

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

    AllOnDifferentNodesAntiAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": [{
            "labelSelector": {
                "matchExpressions": [{
                    "key": "app.kubernetes.io/name",
                    "operator": "In",
                    "values": ["test-cluster"]
                }]
            },
            "topologyKey": "kubernetes.io/hostname"
        }]
    }

    UnAchievablePodAntiAffinity = {
        "requiredDuringSchedulingIgnoredDuringExecution": [{
            "labelSelector": {
                "matchExpressions": [{
                    "key": "app.kubernetes.io/name",
                    "operator": "In",
                    "values": ["test-cluster"]
                }]
            },
            "topologyKey": "kubernetes.io/os"
        }]
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodAntiAffinitySchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return PodAntiAffinitySchema.AllOnDifferentNodesAntiAffinity

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

    AllOnOneNodeAffinity = {
        "nodeAffinity": NodeAffinitySchema.OneNodeAffinity,
    }

    AllOnDifferentNodesAntiAffinity = {
        "podAntiAffinity": PodAntiAffinitySchema.AllOnDifferentNodesAntiAffinity,
    }

    InvalidAffinity = {
        "nodeAffinity": NodeAffinitySchema.UnAchievableNodeAffinity,
    }

    NormalAffinity = {
        "nodeAffinity": NodeAffinitySchema.PlainNodeAffinity,
    }

    def all_on_one_node_precondition(prev) -> bool:
        return prev != AffinitySchema.AllOnOneNodeAffinity

    def all_on_one_node(prev) -> dict:
        return AffinitySchema.AllOnOneNodeAffinity

    def all_on_one_node_setup(prev) -> dict:
        return AffinitySchema.NormalAffinity

    def all_on_different_nodes_precondition(prev) -> bool:
        return prev != AffinitySchema.AllOnDifferentNodesAntiAffinity

    def all_on_different_nodes(prev) -> dict:
        return AffinitySchema.AllOnDifferentNodesAntiAffinity

    def all_on_different_nodes_setup(prev) -> dict:
        return AffinitySchema.NormalAffinity

    def invalid_affinity_precondition(prev) -> bool:
        return prev != AffinitySchema.InvalidAffinity

    def invalid_affinity(prev) -> dict:
        return AffinitySchema.InvalidAffinity

    def invalid_affinity_setup(prev) -> dict:
        return AffinitySchema.NormalAffinity

    AllOnOneNodeTestCase = TestCase(all_on_one_node_precondition, all_on_one_node,
                                    all_on_one_node_setup)
    AllOnDifferentNodesTestCase = TestCase(all_on_different_nodes_precondition,
                                           all_on_different_nodes, all_on_different_nodes_setup)
    InvalidAffinityTestCase = TestCase(invalid_affinity_precondition, invalid_affinity,
                                       invalid_affinity_setup)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in AffinitySchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in AffinitySchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return AffinitySchema.NormalAffinity

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_test_cases = super().test_cases()
        base_test_cases[1].extend([
            AffinitySchema.AllOnOneNodeTestCase, AffinitySchema.AllOnDifferentNodesTestCase,
            AffinitySchema.InvalidAffinityTestCase
        ])
        return base_test_cases

    def __str__(self) -> str:
        return "Affinity"


class PodSecurityContextSchema(K8sObjectSchema):

    def bad_security_context_precondition(prev) -> bool:
        return True

    def bad_security_context(prev) -> dict:
        return {"runAsUser": 500, "runAsGroup": 500, "fsGroup": 500, "supplementalGroups": [500]}

    def bad_security_context_setup(prev) -> dict:
        return {
            "runAsUser": 1000,
            "runAsGroup": 1000,
            "fsGroup": 1000,
            "supplementalGroups": [1000]
        }

    def root_security_context_precondition(prev) -> bool:
        return True

    def root_security_context(prev) -> dict:
        return {"runAsUser": 0, "runAsGroup": 0, "fsGroup": 0, "supplementalGroups": [0]}

    def root_security_context_setup(prev) -> dict:
        return {
            "runAsUser": 1000,
            "runAsGroup": 1000,
            "fsGroup": 1000,
            "supplementalGroups": [1000]
        }

    def normal_security_context_precondition(prev) -> bool:
        return prev != {
            "runAsUser": 1000,
            "runAsGroup": 1000,
            "fsGroup": 1000,
            "supplementalGroups": [1000]
        }

    def normal_security_context(prev) -> dict:
        return {
            "runAsUser": 1000,
            "runAsGroup": 1000,
            "fsGroup": 1000,
            "supplementalGroups": [1000]
        }

    def normal_security_context_setup(prev) -> dict:
        return {"runAsUser": 0, "runAsGroup": 0, "fsGroup": 0, "supplementalGroups": [0]}

    BadSecurityContextTestCase = TestCase(bad_security_context_precondition, bad_security_context,
                                          bad_security_context_setup)
    RootSecurityContextTestCase = TestCase(root_security_context_precondition,
                                           root_security_context, root_security_context_setup)
    NormalSecurityContextTestCase = TestCase(normal_security_context_precondition,
                                             normal_security_context, normal_security_context_setup)

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodSecurityContextSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_test_cases = super().test_cases()
        base_test_cases[1].extend([
            PodSecurityContextSchema.BadSecurityContextTestCase,
            PodSecurityContextSchema.RootSecurityContextTestCase,
            PodSecurityContextSchema.NormalSecurityContextTestCase
        ])
        return base_test_cases

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in SecurityContextSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    PlainToleration = {
        "key": "test-key",
        "operator": "Equal",
        "value": "test-value",
        "effect": "NoSchedule"
    }

    ControlPlaneToleration = {
        "key": "node-role.kubernetes.io/control-plane",
        "operator": "Exists",
        "effect": "NoSchedule"
    }

    def plain_toleration_precondition(prev) -> bool:
        return prev != TolerationSchema.PlainToleration

    def plain_toleration(prev) -> dict:
        return TolerationSchema.PlainToleration

    def plain_toleration_setup(prev) -> dict:
        return {}

    def control_plane_toleration_precondition(prev) -> bool:
        return prev != TolerationSchema.ControlPlaneToleration

    def control_plane_toleration(prev) -> dict:
        return TolerationSchema.ControlPlaneToleration

    def control_plane_toleration_setup(prev) -> dict:
        return TolerationSchema.PlainToleration

    PlainTolerationTestCase = TestCase(plain_toleration_precondition, plain_toleration,
                                       plain_toleration_setup)
    ControlPlaneTolerationTestCase = TestCase(control_plane_toleration_precondition,
                                              control_plane_toleration,
                                              control_plane_toleration_setup)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in TolerationSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in TolerationSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        if minimum:
            return [TolerationSchema.PlainToleration]
        else:
            return [TolerationSchema.PlainToleration, TolerationSchema.ControlPlaneToleration]

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([
            TolerationSchema.PlainTolerationTestCase,
            TolerationSchema.ControlPlaneTolerationTestCase
        ])
        return base_testcases

    def __str__(self) -> str:
        return "Toleration"


class TolerationsSchema(K8sArraySchema):

    item = TolerationSchema

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.item_schema = TolerationSchema(schema_obj.item_schema)

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return TolerationsSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "Tolerations"


class ImageSchema(K8sStringSchema):

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "Image"


class ImagePullPolicySchema(K8sStringSchema):

    def change_image_pull_policy_precondition(prev) -> bool:
        return prev != None

    def change_image_pull_policy(prev) -> str:
        if prev == "Always":
            return "IfNotPresent"
        else:
            return "Always"

    def change_image_pull_policy_setup(prev) -> str:
        return "Always"

    ChangeImagePullPolicyTestCase = TestCase(change_image_pull_policy_precondition,
                                             change_image_pull_policy,
                                             change_image_pull_policy_setup)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].append(ImagePullPolicySchema.ChangeImagePullPolicyTestCase)
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ImagePullPolicy"


class ContainerSchema(K8sObjectSchema):

    fields = {
        "name": K8sStringSchema,
        "image": ImageSchema,
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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in ContainerSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.item_schema = ContainerSchema(schema_obj.item_schema)

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return ContainersSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "Containers"


class HostPathVolumeSource(K8sObjectSchema):

    fields = {"path": K8sStringSchema, "type": K8sStringSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in HostPathVolumeSource.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in HostPathVolumeSource.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "HostPathVolumeSource"


class VolumeSchema(K8sObjectSchema):

    fields = {
        "name": K8sStringSchema,
        "hostPath": HostPathVolumeSource,
        "emptyDir": K8sObjectSchema,
        "gcePersistentDisk": K8sObjectSchema,
        "awsElasticBlockStore": K8sObjectSchema,
        "gitRepo": K8sObjectSchema,
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in VolumeSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.item_schema = VolumeSchema(schema_obj.item_schema)

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in TopologySpreadConstraintSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.item_schema = TopologySpreadConstraintSchema(schema_obj.item_schema)

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return TopologySpreadConstraintsSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "TopologySpreadConstraint"


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

    NodeNameChangeTestcase = TestCase(node_name_change_precondition, node_name_change,
                                      node_name_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return "kind-worker"

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([NodeNameSchema.NodeNameChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "NodeName"


class PreemptionPolicySchema(K8sStringSchema):

    def preemption_policy_change_precondition(prev):
        return prev is not None

    def preemption_policy_change(prev):
        if prev == 'Never':
            return 'PreemptLowerPriority'
        else:
            return 'Never'

    def preemption_policy_change_setup(prev):
        return 'Never'

    PreemptionPolicyChangeTestcase = TestCase(preemption_policy_change_precondition,
                                              preemption_policy_change,
                                              preemption_policy_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'PreemptLowerPriority':
            return 'Never'
        else:
            return 'PreemptLowerPriority'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([PreemptionPolicySchema.PreemptionPolicyChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "PreemptionPolicy"


class PriorityClassNameSchema(K8sStringSchema):

    def priority_class_name_change_precondition(prev):
        return prev is not None

    def priority_class_name_change(prev):
        if prev == 'system-cluster-critical':
            return 'system-node-critical'
        else:
            return 'system-cluster-critical'

    def priority_class_name_change_setup(prev):
        return 'system-cluster-critical'

    PriorityClassNameChangeTestcase = TestCase(priority_class_name_change_precondition,
                                               priority_class_name_change,
                                               priority_class_name_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'system-node-critical':
            return 'system-cluster-critical'
        else:
            return 'system-node-critical'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([PriorityClassNameSchema.PriorityClassNameChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "PriorityClassName"


class ServiceAccountNameSchema(K8sStringSchema):

    def service_account_name_change_precondition(prev):
        return prev is not None

    def service_account_name_change(prev):
        if prev == 'default':
            return 'default1'
        else:
            return 'default'

    def service_account_name_change_setup(prev):
        return 'default'

    ServiceAccountNameChangeTestcase = TestCase(service_account_name_change_precondition,
                                                service_account_name_change,
                                                service_account_name_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return "default"

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ServiceAccountNameSchema.ServiceAccountNameChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ServiceAccountName"


class ConcurrencyPolicySchema(K8sStringSchema):

    def concurrency_policy_change_precondition(prev):
        return prev is not None

    def concurrency_policy_change(prev):
        if prev == 'Forbid':
            return 'Replace'
        else:
            return 'Forbid'

    def concurrency_policy_change_setup(prev):
        return 'Forbid'

    ConcurrencyPolicyChangeTestcase = TestCase(concurrency_policy_change_precondition,
                                               concurrency_policy_change,
                                               concurrency_policy_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'Replace':
            return 'Forbid'
        else:
            return 'Replace'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ConcurrencyPolicySchema.ConcurrencyPolicyChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ConcurrencyPolicy"


class CronJobScheduleSchema(K8sStringSchema):

    def cronjob_schedule_change_precondition(prev):
        return prev is not None

    def cronjob_schedule_change(prev):
        if prev == '0 0 * * *':
            return '0 0 * * *1'
        else:
            return '0 0 * * *'

    def cronjob_schedule_change_setup(prev):
        return '0 0 * * *'

    CronJobScheduleChangeTestcase = TestCase(cronjob_schedule_change_precondition,
                                             cronjob_schedule_change, cronjob_schedule_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return "0 0 * * *"

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([CronJobScheduleSchema.CronJobScheduleChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "CronJobSchedule"


class CronJobSpecSchema(K8sObjectSchema):

    fields = {
        'concurrencyPolicy': ConcurrencyPolicySchema,
        "schedule": CronJobScheduleSchema,
        "startingDeadlineSeconds": K8sIntegerSchema,
        "successfulJobsHistoryLimit": K8sIntegerSchema,
        "suspend": K8sBooleanSchema,
        "failedJobsHistoryLimit": K8sIntegerSchema,
        "jobTemplate": K8sObjectSchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in CronJobSpecSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True


class CronJobSchema(K8sObjectSchema):

    fields = {
        'metadata': K8sObjectSchema,
        'spec': CronJobSpecSchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in CronJobSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def __str__(self) -> str:
        return "CronJob"


class PodSpecSchema(K8sObjectSchema):

    fields = {
        "affinity": AffinitySchema,
        "containers": ContainersSchema,
        "dnsConfig": K8sObjectSchema,
        "dnsPolicy": K8sStringSchema,
        "enableServiceLinks": K8sBooleanSchema,
        "ephemeralContainers": ContainersSchema,
        "initContainers": ContainersSchema,
        "nodeName": K8sStringSchema,
        "nodeSelector": K8sObjectSchema,
        "preemptionPolicy": PreemptionPolicySchema,
        "priority": K8sIntegerSchema,
        "priorityClassName": PriorityClassNameSchema,
        "restartPolicy": K8sStringSchema,
        "runtimeClassName": K8sStringSchema,  # hard to support, need cluster support
        "schedulerName": K8sStringSchema,  # hard to support, need scheduler
        "securityContext": PodSecurityContextSchema,
        "serviceAccountName": ServiceAccountNameSchema,
        "terminationGracePeriodSeconds": K8sIntegerSchema,
        "tolerations": TolerationsSchema,
        "topologySpreadConstraints": K8sArraySchema,
        "volumes": VolumesSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PodTemplateSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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


class UpdateStrategySchema(K8sStringSchema):

    def update_strategy_change_precondition(prev):
        return prev is not None

    def update_strategy_change(prev):
        if prev == 'RollingUpdate':
            return 'OnDelete'
        else:
            return 'RollingUpdate'

    def update_strategy_change_setup(prev):
        return 'RollingUpdate'

    UpdateStrategyChangeTestcase = TestCase(update_strategy_change_precondition,
                                            update_strategy_change, update_strategy_change_setup)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.default = 'RollingUpdate'

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'OnDelete':
            return 'RollingUpdate'
        else:
            return 'OnDelete'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([UpdateStrategySchema.UpdateStrategyChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "UpdateStrategy"


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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in StatefulSetSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in StatefulSetSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    ServiceTypeChangeTestcase = TestCase(service_type_change_precondition, service_type_change,
                                         service_type_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'LoadBalancer':
            return 'ClusterIP'
        else:
            return 'LoadBalancer'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ServiceTypeSchema.ServiceTypeChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "ServiceType"


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


class AccessModeSchema(K8sStringSchema):

    def change_access_mode_precondition(prev):
        return prev is not None

    def change_access_mode(prev):
        if prev == 'ReadWriteOnce':
            return 'ReadWriteMany'
        else:
            return 'ReadWriteOnce'

    def change_access_mode_setup(prev):
        return 'ReadWriteOnce'

    AccessModeChangeTestcase = TestCase(change_access_mode_precondition, change_access_mode,
                                        change_access_mode_setup)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.enum = ['ReadWriteOnce', 'ReadOnlyMany', 'ReadWriteMany', 'ReadWriteOncePod']

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'ReadWriteOnce':
            return 'ReadOnlyMany'
        else:
            return 'ReadWriteOnce'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([AccessModeSchema.AccessModeChangeTestcase])
        return base_testcases

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "AccessMode"


class StorageClassNameSchema(K8sStringSchema):

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.default = 'standard'

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return 'standard'

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "StorageClassName"


class PersistentVolumeClaimSpecSchema(K8sObjectSchema):

    fields = {
        "accessModes": AccessModeSchema,
        "dataSource": K8sObjectSchema,
        "resources": StorageResourceRequirementsSchema,
        "selector": K8sObjectSchema,
        "storageClassName": K8sStringSchema,
        "volumeMode": K8sStringSchema,  # Filesystem or Block
        "volumeName": K8sStringSchema
    }

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PersistentVolumeClaimSpecSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in PersistentVolumeClaimSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

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