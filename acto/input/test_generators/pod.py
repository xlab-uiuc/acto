# pylint: disable=unused-argument
import enum

from acto.input.test_generators.generator import generator
from acto.input.testcase import TestCase
from acto.schema.array import ArraySchema
from acto.schema.object import ObjectSchema
from acto.schema.string import StringSchema

UnAchievableNodeAffinity = {
    "requiredDuringSchedulingIgnoredDuringExecution": {
        "nodeSelectorTerms": [
            {
                "matchExpressions": [
                    {
                        "key": "kubernetes.io/hostname",
                        "operator": "In",
                        "values": [
                            "NULL",
                        ],
                    }
                ]
            }
        ]
    }
}

AllOnOneNodePodAffinity = {
    "requiredDuringSchedulingIgnoredDuringExecution": [
        {
            "labelSelector": {
                "matchExpressions": [
                    {
                        "key": "app.kubernetes.io/name",
                        "operator": "In",
                        "values": ["test-cluster"],
                    }
                ]
            },
            "topologyKey": "kubernetes.io/hostname",
        }
    ]
}

PlainNodeAffinity = {
    "requiredDuringSchedulingIgnoredDuringExecution": {
        "nodeSelectorTerms": [
            {
                "matchExpressions": [
                    {
                        "key": "kubernetes.io/hostname",
                        "operator": "In",
                        "values": [
                            "kind-worker",
                            "kind-worker2",
                            "kind-worker3",
                            "kind-control-plane",
                        ],
                    }
                ]
            }
        ]
    }
}

PlainPodAffinity = {
    "requiredDuringSchedulingIgnoredDuringExecution": [
        {
            "labelSelector": {
                "matchExpressions": [
                    {
                        "key": "app.kubernetes.io/name",
                        "operator": "In",
                        "values": ["test-cluster"],
                    }
                ]
            },
            "topologyKey": "kubernetes.io/os",
        }
    ]
}

UnAchievablePodAffinity = {
    "requiredDuringSchedulingIgnoredDuringExecution": [
        {
            "labelSelector": {
                "matchExpressions": [
                    {
                        "key": "app.kubernetes.io/name",
                        "operator": "In",
                        "values": ["test-cluster"],
                    }
                ]
            },
            "topologyKey": "NULL",
        }
    ]
}

AllOnDifferentNodesAntiAffinity = {
    "requiredDuringSchedulingIgnoredDuringExecution": [
        {
            "labelSelector": {
                "matchExpressions": [
                    {
                        "key": "app.kubernetes.io/name",
                        "operator": "In",
                        "values": ["test-cluster"],
                    }
                ]
            },
            "topologyKey": "kubernetes.io/hostname",
        }
    ]
}

AllOnOneNodePodAffinity = {
    "requiredDuringSchedulingIgnoredDuringExecution": [
        {
            "labelSelector": {
                "matchExpressions": [
                    {
                        "key": "app.kubernetes.io/name",
                        "operator": "In",
                        "values": ["test-cluster"],
                    }
                ]
            },
            "topologyKey": "kubernetes.io/hostname",
        }
    ]
}


class AffinityValues(enum.Enum):
    """Some predefined values for affinity"""

    ALL_ON_ONE_NODE = {
        "podAffinity": AllOnOneNodePodAffinity,
    }
    PLAIN = {
        "nodeAffinity": PlainNodeAffinity,
    }
    UNACHIEVABLE = {
        "nodeAffinity": UnAchievableNodeAffinity,
    }
    ALL_ON_DIFFERENT_NODES = {
        "podAntiAffinity": AllOnDifferentNodesAntiAffinity,
    }


@generator(k8s_schema_name="core.v1.Affinity")
def affinity_tests(schema: ObjectSchema) -> list[TestCase]:
    """Test generator for CoreV1 Affinity"""
    all_on_one_node_test = TestCase(
        name="k8s-all_on_one_node",
        precondition=lambda x: x != AffinityValues.ALL_ON_ONE_NODE,
        mutator=lambda x: AffinityValues.ALL_ON_ONE_NODE,
        setup=lambda x: None,
    )
    all_on_different_nodes_test = TestCase(
        name="k8s-all_on_different_nodes",
        precondition=lambda x: x != AffinityValues.ALL_ON_DIFFERENT_NODES,
        mutator=lambda x: AffinityValues.ALL_ON_DIFFERENT_NODES,
        setup=lambda x: None,
    )
    invalid_test = TestCase(
        name="k8s-invalid_affinity",
        precondition=lambda x: x != AffinityValues.ALL_ON_DIFFERENT_NODES,
        mutator=lambda x: AffinityValues.ALL_ON_DIFFERENT_NODES,
        setup=lambda x: None,
    )
    null_test = TestCase(
        name="k8s-null_affinity",
        precondition=lambda x: x is not None,
        mutator=lambda x: None,
        setup=lambda x: AffinityValues.ALL_ON_DIFFERENT_NODES,
    )
    return [
        all_on_one_node_test,
        all_on_different_nodes_test,
        invalid_test,
        null_test,
    ]


class PodSecurityContextValues(enum.Enum):
    """Some predefined values for PodSecurityContext"""

    DEFAULT = {
        "runAsGroup": 1000,
        "runAsUser": 1000,
        "supplementalGroups": [1000],
    }
    ROOT = {
        "runAsGroup": 0,
        "runAsUser": 0,
        "supplementalGroups": [0],
    }
    BAD = {
        "runAsUser": 500,
        "runAsGroup": 500,
        "fsGroup": 500,
        "supplementalGroups": [500],
    }


@generator(k8s_schema_name="core.v1.PodSecurityContext")
def pod_security_context_tests(schema: ObjectSchema) -> list[TestCase]:
    """Test generator for PodSecurityContext"""
    bad_security_context_test = TestCase(
        name="k8s-bad_security_context",
        precondition=lambda x: x != PodSecurityContextValues.BAD,
        mutator=lambda x: PodSecurityContextValues.BAD,
        setup=lambda x: None,
    )
    root_security_context_test = TestCase(
        name="k8s-root_security_context",
        precondition=lambda x: x != PodSecurityContextValues.ROOT,
        mutator=lambda x: PodSecurityContextValues.ROOT,
        setup=lambda x: None,
    )
    normal_security_context_test = TestCase(
        name="k8s-normal_security_context",
        precondition=lambda x: x != PodSecurityContextValues.DEFAULT,
        mutator=lambda x: PodSecurityContextValues.DEFAULT,
        setup=lambda x: None,
    )
    return [
        bad_security_context_test,
        root_security_context_test,
        normal_security_context_test,
    ]


class TolerationValues(enum.Enum):
    """Some predefined values for Toleration"""

    PLAIN = {
        "key": "test-key",
        "operator": "Equal",
        "value": "test-value",
        "effect": "NoExecute",
        "tolerationSeconds": 3600,
    }
    CONTROL_PLANE_TOLERATION = {
        "key": "node-role.kubernetes.io/control-plane",
        "operator": "Exists",
        "effect": "NoExecute",
        "tolerationSeconds": 3600,
    }
    INVALID = {
        "key": "test-key",
        "operator": "Equal",
        "value": "test-value",
        "effect": "INVALID_EFFECT",
        "tolerationSeconds": 0,
    }


@generator(k8s_schema_name="core.v1.Toleration")
def toleration_tests(schema: ObjectSchema) -> list[TestCase]:
    """Test generator for Toleration"""
    plain_toleration_test = TestCase(
        name="k8s-plain_toleration",
        precondition=lambda x: x != TolerationValues.PLAIN,
        mutator=lambda x: TolerationValues.PLAIN,
        setup=lambda x: None,
    )
    control_plane_toleration_test = TestCase(
        name="k8s-control_plane_toleration",
        precondition=lambda x: x != TolerationValues.CONTROL_PLANE_TOLERATION,
        mutator=lambda x: TolerationValues.CONTROL_PLANE_TOLERATION,
        setup=lambda x: None,
    )
    invalid_toleration_test = TestCase(
        name="k8s-invalid_toleration",
        precondition=lambda x: x != TolerationValues.INVALID,
        mutator=lambda x: TolerationValues.INVALID,
        setup=lambda x: None,
    )
    return [
        plain_toleration_test,
        control_plane_toleration_test,
        invalid_toleration_test,
    ]


@generator(k8s_schema_name="core.v1.Tolerations")
def tolerations_tests(schema: ArraySchema) -> list[TestCase]:
    """Test generator for Tolerations"""
    tolerations_pop_test = TestCase(
        name="k8s-tolerations_pop",
        precondition=lambda x: x and len(x) > 0,
        mutator=lambda x: x[:-1],
        setup=lambda x: [TolerationValues.PLAIN],
    )
    return [tolerations_pop_test]


class ImagePullPolicyValues(enum.Enum):
    """Some predefined values for ImagePullPolicy"""

    ALWAYS = "Always"
    NEVER = "Never"
    IF_NOT_PRESENT = "IfNotPresent"


@generator(field_name="imagePullPolicy")
def image_pull_policy_tests(schema: StringSchema) -> list[TestCase]:
    """Test generator for imagePullPolicy"""
    change_test = TestCase(
        name="k8s-change_image_pull_policy",
        precondition=lambda x: x != ImagePullPolicyValues.ALWAYS,
        mutator=lambda x: ImagePullPolicyValues.ALWAYS,
        setup=lambda x: ImagePullPolicyValues.NEVER,
    )
    invalid_test = TestCase(
        name="k8s-invalid_image_pull_policy",
        precondition=lambda x: True,
        mutator=lambda x: "INVALID_IMAGE_PULL_POLICY",
        setup=lambda x: ImagePullPolicyValues.NEVER,
    )
    return [change_test, invalid_test]


@generator(k8s_schema_name="core.v1.GRPCAction")
def grpc_action_tests(schema: ObjectSchema) -> list[TestCase]:
    """Test generator for grpc action"""
    invalid_test = TestCase(
        name="k8s-invalid_grpc_action",
        precondition=lambda x: True,
        mutator=lambda x: {"port": 1234, "service": "invalid-service"},
        setup=lambda x: None,
    )
    return [invalid_test]


@generator(k8s_schema_name="core.v1.Probe")
def liveness_probe_tests(schema: ObjectSchema) -> list[TestCase]:
    """Test generator for liveness probe"""
    invalid_test = TestCase(
        name="k8s-http_probe",
        precondition=lambda x: True,
        mutator=lambda x: {"httpGet": {"path": "/invalid-path"}},
        setup=lambda x: None,
    )
    invalid_tcp_test = TestCase(
        name="k8s-tcp_probe",
        precondition=lambda x: True,
        mutator=lambda x: {"tcpSocket": {"port": 1234}},
        setup=lambda x: None,
    )
    invalid_exec_test = TestCase(
        name="k8s-exec_probe",
        precondition=lambda x: True,
        mutator=lambda x: {"exec": {"command": ["invalid-command"]}},
        setup=lambda x: None,
    )
    return [invalid_test, invalid_tcp_test, invalid_exec_test]


@generator(k8s_schema_name="core.v1.Container")
def container_tests(schema: ObjectSchema) -> list[TestCase]:
    """Test generator for container"""
    invalid_test = TestCase(
        name="k8s-container_invalid_name",
        precondition=lambda x: True,
        mutator=lambda x: {"name": "INVALID_NAME", "image": "nginx"},
        setup=lambda x: None,
    )
    return [invalid_test]


@generator(field_name="name")
def invalid_name_tests(schema: StringSchema) -> list[TestCase]:
    """Test generator for invalid name"""
    # TODO: inherit basic tests
    invalid_test = TestCase(
        name="invalid-name",
        precondition=lambda x: True,
        mutator=lambda x: "INVALID_NAME",
        setup=lambda x: None,
    )
    return [invalid_test]


class PreemptionPolicyValues(enum.Enum):
    """Some predefined values for PreemptionPolicy"""

    NEVER = "Never"
    PREMEPTION_LOW_PRIORITY = "PreemptLowerPriority"


@generator(field_name="preemptionPolicy")
def preemption_policy_tests(schema: StringSchema) -> list[TestCase]:
    """Test generator for preemption policy"""
    policy_change_test = TestCase(
        name="k8s-change_preemption_policy",
        precondition=lambda x: x != PreemptionPolicyValues.NEVER,
        mutator=lambda x: PreemptionPolicyValues.NEVER,
        setup=lambda x: PreemptionPolicyValues.PREMEPTION_LOW_PRIORITY,
    )
    return [policy_change_test]


@generator(field_name="restartPolicy")
def restart_policy_tests(schema: StringSchema) -> list[TestCase]:
    """Test generator for restart policy"""
    invalid_test = TestCase(
        name="k8s-invalid_restart_policy",
        precondition=lambda x: True,
        mutator=lambda x: "INVALID_RESTART_POLICY",
        setup=lambda x: None,
    )
    change_test = TestCase(
        name="k8s-restart_policy_change",
        precondition=lambda x: x != "Always",
        mutator=lambda x: "Always",
        setup=lambda x: "Never",
    )
    return [invalid_test, change_test]


@generator(field_name="priorityClassName")
def priority_class_name_tests(schema: StringSchema) -> list[TestCase]:
    """Test generator for priority class name"""
    invalid_test = TestCase(
        name="k8s-invalid_priority_class_name",
        precondition=lambda x: True,
        mutator=lambda x: "INVALID_PRIORITY_CLASS_NAME",
        setup=lambda x: None,
    )
    change_test = TestCase(
        name="k8s-priority_class_name_change",
        precondition=lambda x: x != "system-cluster-critical",
        mutator=lambda x: "system-cluster-critical",
        setup=lambda x: "system-node-critical",
    )
    return [invalid_test, change_test]


@generator(field_name="serviceAccountName")
def service_account_name_tests(schema: StringSchema) -> list[TestCase]:
    """Test generator for service account name"""
    invalid_test = TestCase(
        name="invalid-service-account-name",
        precondition=lambda x: True,
        mutator=lambda x: "INVALID_SERVICE_ACCOUNT_NAME",
        setup=lambda x: None,
    )
    change_test = TestCase(
        name="k8s-service_account_name_change",
        precondition=lambda x: x != "default",
        mutator=lambda x: "default",
        setup=lambda x: "system:serviceaccount:default:default",
    )
    return [invalid_test, change_test]


@generator(field_name="whenUnsatisfiable")
def when_unsatisfiable_tests(schema: StringSchema) -> list[TestCase]:
    """Test generator for when unsatisfiable"""
    invalid_test = TestCase(
        name="k8s-invalid_value",
        precondition=lambda x: True,
        mutator=lambda x: "INVALID_WHEN_UNSATISFIABLE",
        setup=lambda x: None,
    )
    change_test = TestCase(
        name="k8s-when_unsatisfiable_change",
        precondition=lambda x: x != "ScheduleAnyway",
        mutator=lambda x: "ScheduleAnyway",
        setup=lambda x: None,
    )
    return [invalid_test, change_test]


@generator(k8s_schema_name="core.v1.TopologySpreadConstraint")
def topology_spread_constraint_tests(schema: ObjectSchema) -> list[TestCase]:
    """Test generator for topology spread constraint"""
    invalid_test = TestCase(
        name="k8s-invalid_topology_spread_constraint",
        precondition=lambda x: True,
        mutator=lambda x: {"topologyKey": "INVALID_TOPOLOGY_KEY"},
        setup=lambda x: None,
    )
    return [invalid_test]
