# pylint: disable=unused-argument
from acto.input.test_generators.generator import generator
from acto.input.testcase import Store, TestCase
from acto.schema.integer import IntegerSchema
from acto.schema.object import ObjectSchema


def scale_down_up_precondition(prev, store: Store) -> bool:
    """Precondition for scaleDownUp test case"""
    if store.data is None:
        store.data = True
        return False
    else:
        return True


def scale_up_down_precondition(prev, store: Store) -> bool:
    """Precondition for scaleUpDown test case"""
    if store.data is None:
        store.data = True
        return False
    else:
        return True


@generator(field_name="replicas")
def replicas_tests(schema: IntegerSchema) -> list[TestCase]:
    """Generate test cases for replicas field"""
    invalid_test = TestCase(
        "k8s-invalid_replicas",
        lambda x: True,
        lambda x: 0,
        lambda x: 1,
        invalid=True,
        semantic=True,
    )
    scale_down_up_test = TestCase(
        "k8s-scaleDownUp",
        scale_down_up_precondition,
        lambda x: 4 if x is None else x + 2,
        lambda x: 1 if x is None else x - 2,
        Store(),
        semantic=True,
    )
    scale_up_down_test = TestCase(
        "k8s-scaleUpDown",
        scale_up_down_precondition,
        lambda x: 1 if x is None else x - 2,
        lambda x: 5 if x is None else x + 2,
        Store(),
        semantic=True,
    )
    overload_test = TestCase(
        "k8s-overload",
        lambda x: True,
        lambda x: 1000,
        lambda x: 1,
        invalid=True,
        semantic=True,
    )
    return [invalid_test, scale_down_up_test, scale_up_down_test, overload_test]


@generator(field_name="StatefulSetUpdateStrategy")
def stateful_set_update_strategy_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for StatefulSetUpdateStrategy field"""
    invalid_test = TestCase(
        "k8s-invalid_update_strategy",
        lambda x: True,
        lambda x: {"type": "INVALID_STATEFUL_SET_UPDATE_STRATEGY"},
        lambda x: None,
        invalid=True,
        semantic=True,
    )
    change_test = TestCase(
        "k8s-update_strategy_change",
        lambda x: x != {"type": "RollingUpdate"},
        lambda x: {"type": "RollingUpdate"},
        lambda x: {"type": "OnDelete"},
        semantic=True,
    )
    return [invalid_test, change_test]
