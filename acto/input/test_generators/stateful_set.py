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
        "invalid-replicas",
        lambda x: True,
        lambda x: 0,
        lambda x: 1,
    )
    scale_down_up_test = TestCase(
        "replicas-scaleDownUp",
        scale_down_up_precondition,
        lambda x: 4 if x is None else x + 2,
        lambda x: 1 if x is None else x - 2,
        Store(),
    )
    scale_up_down_test = TestCase(
        "replicas-scaleUpDown",
        scale_up_down_precondition,
        lambda x: 1 if x is None else x - 2,
        lambda x: 5 if x is None else x + 2,
        Store(),
    )
    overload_test = TestCase(
        "replicas-overload",
        lambda x: True,
        lambda x: 1000,
        lambda x: 1,
    )
    return [invalid_test, scale_down_up_test, scale_up_down_test, overload_test]


@generator(field_name="StatefulSetUpdateStrategy")
def stateful_set_update_strategy_tests(schema: ObjectSchema) -> list[TestCase]:
    """Generate test cases for StatefulSetUpdateStrategy field"""
    invalid_test = TestCase(
        "invalid-statefulSetUpdateStrategy",
        lambda x: True,
        lambda x: {"type": "INVALID_STATEFUL_SET_UPDATE_STRATEGY"},
        lambda x: None,
    )
    change_test = TestCase(
        "statefulSetUpdateStrategy-change",
        lambda x: x != {"type": "RollingUpdate"},
        lambda x: {"type": "RollingUpdate"},
        lambda x: {"type": "OnDelete"},
    )
    return [invalid_test, change_test]
