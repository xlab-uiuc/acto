from typing import Callable, Any, Union

from acto.utils import get_thread_logger


class Store:

    def __init__(self) -> None:
        self.data = None


class TestCase:
    # disable pytest to collect this class
    __test__ = False

    def __init__(self,
                 name: str,
                 precondition: Union[Callable[[Any], bool], Callable[[Any, Store], bool]],
                 mutator: Callable[[Any], Any],
                 setup: Callable[[Any], Any],
                 store: Store = None) -> None:
        """Class represent a test case

        Args:
            name: the name of the test case
            precondition: a function returns whether the previous value
                satisfies the test case's precondition
            mutator: a function to change the value to execute the test case
            setup: a function to set up the precondition if the precondition
                fails, so that we can run this test case next time
        """

        self.name = name
        self.preconditions = [precondition]
        self.mutator = mutator
        self.setup = setup
        self.store = store

    def test_precondition(self, prev) -> bool:
        logger = get_thread_logger(with_prefix=True)

        ret = True
        for precondition in self.preconditions:
            if self.store is not None:
                ret = ret and precondition(prev, self.store)
            else:
                ret = ret and precondition(prev)
            logger.debug('Precondition [%s] Result [%s]' % (precondition.__name__, ret))

        return ret

    def run_setup(self, prev):
        return self.setup(prev)

    def add_precondition(self, precondition: callable):
        self.preconditions.append(precondition)

    def __str__(self) -> str:
        return self.name

    def to_dict(self) -> dict:
        ret = {
            'precondition': list(map(lambda x: x.__name__, self.preconditions)),
            'mutator': self.mutator.__name__
        }
        return ret

    def signature(self, field: str, **kwargs) -> dict:
        return {
            'field': field,
            'testcase': str(self),
            **kwargs
        }


class K8sTestCase(TestCase):
    """Class represent a test case for k8s, purely for test case name purposes"""

    def __init__(self,
                 precondition: Callable,
                 mutator: Callable,
                 setup: Callable,
                 store: Store = None) -> None:
        name = f'k8s-{mutator.__name__}'
        super().__init__(name, precondition, mutator, setup, store)


class K8sInvalidTestCase(K8sTestCase):
    """Class represent a test case for k8s, purely for test case name purposes"""

    def __init__(self,
                 precondition: Callable,
                 mutator: Callable,
                 setup: Callable,
                 store: Store = None) -> None:
        super().__init__(precondition, mutator, setup, store)


class EnumTestCase(TestCase):

    def __init__(self, case) -> None:
        self.case = case
        super().__init__(case, self.enum_precondition, self.enum_mutator, self.setup)

    @staticmethod
    def enum_precondition(_):
        return True

    def enum_mutator(self, _):
        return self.case

    @staticmethod
    def setup(_):
        """Never going to be called"""
        # FIXME: assert happens for rabbitmq's service.type field
        assert ()


class SchemaPrecondition:
    # XXX: Probably could use partial

    def __init__(self, schema) -> None:
        self.schema = schema

    def precondition(self, prev):
        return self.schema.validate(prev)
