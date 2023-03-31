from typing import List, Tuple
from schema import AnyOfSchema, ArraySchema, BaseSchema, BooleanSchema, IntegerSchema, ObjectSchema, StringSchema, extract_schema
from known_schemas.base import K8sStringSchema, K8sObjectSchema, K8sArraySchema, K8sIntegerSchema, K8sBooleanSchema
from schema import BaseSchema
from test_case import TestCase, K8sTestCase

from .resource_schemas import ComputeResourceRequirementsSchema, ResourceRequirementsSchema


class EnvVarSchema(K8sObjectSchema):

    fields = {"name": K8sStringSchema, "value": K8sStringSchema}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in EnvVarSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in EnvVarSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True


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

    def null_affinity_precondition(prev) -> bool:
        return prev != None

    def null_affinity(prev) -> dict:
        return None

    def null_affinity_setup(prev) -> dict:
        return AffinitySchema.NormalAffinity

    AllOnOneNodeTestCase = K8sTestCase(all_on_one_node_precondition, all_on_one_node,
                                       all_on_one_node_setup)
    AllOnDifferentNodesTestCase = K8sTestCase(all_on_different_nodes_precondition,
                                              all_on_different_nodes, all_on_different_nodes_setup)
    InvalidAffinityTestCase = K8sTestCase(invalid_affinity_precondition, invalid_affinity,
                                          invalid_affinity_setup)

    NullAffinityTestCase = K8sTestCase(null_affinity_precondition, null_affinity,
                                       null_affinity_setup)

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
            AffinitySchema.InvalidAffinityTestCase, AffinitySchema.NullAffinityTestCase
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
        return prev != {"runAsUser": 0, "runAsGroup": 0, "fsGroup": 0}

    def root_security_context(prev) -> dict:
        return {"runAsUser": 0, "runAsGroup": 0, "fsGroup": 0}

    def root_security_context_setup(prev) -> dict:
        return {"runAsUser": 1000, "runAsGroup": 1000, "fsGroup": 1000}

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

    BadSecurityContextTestCase = K8sTestCase(bad_security_context_precondition,
                                             bad_security_context, bad_security_context_setup)
    RootSecurityContextTestCase = K8sTestCase(root_security_context_precondition,
                                              root_security_context, root_security_context_setup)
    NormalSecurityContextTestCase = K8sTestCase(normal_security_context_precondition,
                                                normal_security_context,
                                                normal_security_context_setup)

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

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        return {
            "runAsUser": 1000,
            "runAsGroup": 1000,
            "fsGroup": 1000,
        }

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

    PlainTolerationTestCase = K8sTestCase(plain_toleration_precondition, plain_toleration,
                                          plain_toleration_setup)
    ControlPlaneTolerationTestCase = K8sTestCase(control_plane_toleration_precondition,
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
        return TolerationSchema.PlainToleration

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

    def tolerations_pop_precondition(prev) -> bool:
        return len(prev) > 0

    def tolerations_pop(prev) -> list:
        return []

    def tolerations_pop_setup(prev) -> list:
        return [TolerationSchema.PlainToleration]

    TolerationsPopTestCase = K8sTestCase(tolerations_pop_precondition, tolerations_pop,
                                         tolerations_pop_setup)

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.item_schema = TolerationSchema(schema_obj.item_schema)

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return TolerationsSchema.item.Match(schema.get_item_schema())

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs) -> list:
        if minimum:
            return [TolerationSchema.PlainToleration]
        else:
            return [TolerationSchema.PlainToleration, TolerationSchema.ControlPlaneToleration]

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([TolerationsSchema.TolerationsPopTestCase])
        return base_testcases

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

    ChangeImagePullPolicyTestCase = K8sTestCase(change_image_pull_policy_precondition,
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


class GRPCSchema(K8sObjectSchema):

    fields = {
        "port": K8sIntegerSchema,
        "service": K8sStringSchema,
    }

    def invalid_grpc_precondition(prev) -> bool:
        return True

    def invalid_grpc(prev) -> dict:
        return {"port": 1234, "service": "invalid-service"}

    def invalid_grpc_setup(prev) -> dict:
        return {"port": 1234, "service": "invalid-service"}

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        for field, field_schema in GRPCSchema.fields.items():
            if field in schema_obj.properties:
                self.properties[field] = field_schema(schema_obj.properties[field])

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in GRPCSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].append(
            TestCase(GRPCSchema.invalid_grpc_precondition, GRPCSchema.invalid_grpc,
                     GRPCSchema.invalid_grpc_setup))
        return base_testcases

    def __str__(self) -> str:
        return "GRPC"


class LivenessProbeSchema(K8sObjectSchema):

    def tcp_probe_precondition(prev) -> bool:
        return True

    def tcp_probe(prev) -> dict:
        return {"tcpSocket": {"port": 8500}, "initialDelaySeconds": 10}

    def tcp_probe_setup(prev) -> dict:
        return {"tcpSocket": {"port": 12345}, "initialDelaySeconds": 10}

    def http_probe_precondition(prev) -> bool:
        return True

    def http_probe(prev) -> dict:
        return {"httpGet": {"port": 8500}, "initialDelaySeconds": 10}

    def http_probe_setup(prev) -> dict:
        return {"httpGet": {"port": 12345}, "initialDelaySeconds": 10}

    def grpc_probe_precondition(prev) -> bool:
        return True

    def grpc_probe(prev) -> dict:
        return {"grpc": {"port": 8500}, "initialDelaySeconds": 10}

    def grpc_probe_setup(prev) -> dict:
        return {"grpc": {"port": 12345}, "initialDelaySeconds": 10}

    def exec_probe_precondition(prev) -> bool:
        return True

    def exec_probe(prev) -> dict:
        return {"exec": {"command": ["/liveness.sh"]}, "initialDelaySeconds": 10}

    def exec_probe_setup(prev) -> dict:
        return {"exec": {"command": ["/liveness.sh"]}, "initialDelaySeconds": 10}

    def invalid_probe_precondition(prev) -> bool:
        return True

    def invalid_probe(prev) -> dict:
        return {"invalid": {"port": 8500}, "initialDelaySeconds": 10}

    def invalid_probe_setup(prev) -> dict:
        return {"invalid": {"port": 12345}, "initialDelaySeconds": 10}

    TCP_PROBE_TESTCASE = K8sTestCase(tcp_probe_precondition, tcp_probe, tcp_probe_setup)
    HTTP_PROBE_TESTCASE = K8sTestCase(http_probe_precondition, http_probe, http_probe_setup)
    GRPC_PROBE_TESTCASE = K8sTestCase(grpc_probe_precondition, grpc_probe, grpc_probe_setup)
    EXEC_PROBE_TESTCASE = K8sTestCase(exec_probe_precondition, exec_probe, exec_probe_setup)

    fields = {
        "exec": K8sObjectSchema,
        "httpGet": K8sObjectSchema,
        "tcpSocket": K8sObjectSchema,
        "grpc": GRPCSchema,
        "initialDelaySeconds": K8sIntegerSchema,
        "timeoutSeconds": K8sIntegerSchema,
        "periodSeconds": K8sIntegerSchema,
        "successThreshold": K8sIntegerSchema,
        "failureThreshold": K8sIntegerSchema,
    }

    def Match(schema: ObjectSchema) -> bool:
        if not K8sObjectSchema.Match(schema):
            return False
        for field, field_schema in LivenessProbeSchema.fields.items():
            if field not in schema.properties:
                return False
            elif not field_schema.Match(schema.properties[field]):
                return False
        return True

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].append(LivenessProbeSchema.TCP_PROBE_TESTCASE)
        base_testcases[1].append(LivenessProbeSchema.HTTP_PROBE_TESTCASE)
        base_testcases[1].append(LivenessProbeSchema.GRPC_PROBE_TESTCASE)
        base_testcases[1].append(LivenessProbeSchema.EXEC_PROBE_TESTCASE)
        return base_testcases

    def __str__(self) -> str:
        return "LivenessProbe"


class ArgsSchema(K8sArraySchema):

    item = K8sStringSchema

    def __init__(self, schema_obj: BaseSchema) -> None:
        super().__init__(schema_obj)
        self.item_schema = K8sStringSchema(schema_obj.item_schema)

    def Match(schema: ObjectSchema) -> bool:
        if not K8sArraySchema.Match(schema):
            return False
        else:
            return ArgsSchema.item.Match(schema.get_item_schema())

    def __str__(self) -> str:
        return "Args"


class ContainerSchema(K8sObjectSchema):

    def container_invalid_name_precondition(prev) -> bool:
        return True

    def container_invalid_name(prev) -> dict:
        return {"name": "INVALIDNAME", "image": "ubuntu"}

    def container_invalid_name_setup(prev) -> dict:
        return {"name": "INVALIDNAME", "image": "ubuntu"}

    ContainerInvalidNameTestCase = K8sTestCase(container_invalid_name_precondition,
                                               container_invalid_name, container_invalid_name_setup)

    fields = {
        "name": K8sStringSchema,
        "image": ImageSchema,
        "command": K8sArraySchema,
        "args": ArgsSchema,
        "workingDir": K8sStringSchema,
        "ports": K8sArraySchema,
        "env": K8sArraySchema,
        "resources": ComputeResourceRequirementsSchema,
        "volumeMounts": K8sArraySchema,
        "livenessProbe": LivenessProbeSchema,
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

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([ContainerSchema.ContainerInvalidNameTestCase])
        return super().test_cases()

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

    PreemptionPolicyChangeTestcase = K8sTestCase(preemption_policy_change_precondition,
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


class RestartPolicySchema(K8sStringSchema):

    def restart_policy_change_precondition(prev):
        return prev is not None

    def restart_policy_change(prev):
        if prev == 'Always':
            return 'OnFailure'
        else:
            return 'Always'

    def restart_policy_change_setup(prev):
        return 'Always'

    RestartPolicyChangeTestcase = K8sTestCase(restart_policy_change_precondition,
                                              restart_policy_change, restart_policy_change_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        if exclude_value == 'OnFailure':
            return 'Always'
        else:
            return 'OnFailure'

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([RestartPolicySchema.RestartPolicyChangeTestcase])
        return super().test_cases()

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def __str__(self) -> str:
        return "RestartPolicy"


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

    PriorityClassNameChangeTestcase = K8sTestCase(priority_class_name_change_precondition,
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

    ServiceAccountNameChangeTestcase = K8sTestCase(service_account_name_change_precondition,
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


class WhenUnsatifiableSchema(K8sStringSchema):

    def invalid_value_precondition(prev):
        return prev is not None

    def invalid_value(prev):
        return "INVALID"

    def invalid_value_setup(prev):
        return "DoNotSchedule"

    InvalidValueTestcase = K8sTestCase(invalid_value_precondition, invalid_value,
                                       invalid_value_setup)

    def gen(self, exclude_value=None, minimum: bool = False, **kwargs):
        return "ScheduleAnyway"

    def Match(schema: ObjectSchema) -> bool:
        return K8sStringSchema.Match(schema)

    def test_cases(self) -> Tuple[List[TestCase], List[TestCase]]:
        base_testcases = super().test_cases()
        base_testcases[1].extend([WhenUnsatifiableSchema.InvalidValueTestcase])
        return super().test_cases()

    def __str__(self) -> str:
        return "WhenUnsatifiable"


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
        "restartPolicy": RestartPolicySchema,
        "runtimeClassName": K8sStringSchema,  # hard to support, need cluster support
        "schedulerName": K8sStringSchema,  # hard to support, need scheduler
        "securityContext": PodSecurityContextSchema,
        "serviceAccountName": ServiceAccountNameSchema,
        "terminationGracePeriodSeconds": K8sIntegerSchema,
        "tolerations": TolerationsSchema,
        "topologySpreadConstraints": TopologySpreadConstraintsSchema,
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
