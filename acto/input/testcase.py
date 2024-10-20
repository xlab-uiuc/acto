import dataclasses
import functools
from typing import Any, Callable, Optional, Union

from acto.utils import get_thread_logger


@dataclasses.dataclass
class Store:
    """A store to store data for test cases"""

    def __init__(self) -> None:
        self.data: Any = None


class TestCase:
    """Class represent a test case"""

    # disable pytest to collect this class
    __test__ = False

    def __init__(
        self,
        name: str,
        precondition: Union[
            Callable[[Any], bool], Callable[[Any, Store], bool]
        ],
        mutator: Callable[[Any], Any],
        setup: Callable[[Any], Any],
        store: Optional[Store] = None,
        primitive: bool = False,
        semantic: bool = False,
        invalid: bool = False,
        kubernetes_schema: bool = False,
    ) -> None:
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

        # test attributes
        self.primitive = primitive
        self.semantic = semantic
        self.invalid = invalid
        self.kubernetes_schema = kubernetes_schema

    def test_precondition(self, prev) -> bool:
        """Test whether the previous value satisfies the precondition"""
        logger = get_thread_logger(with_prefix=True)

        ret = True
        for precondition in self.preconditions:
            if self.store is not None:
                ret = ret and precondition(prev, self.store)
            else:
                ret = ret and precondition(prev)
            precondition_name = (
                precondition.func.__name__
                if isinstance(precondition, functools.partial)
                else precondition.__name__
            )
            logger.debug(
                "Precondition [%s] Result [%s]", precondition_name, ret
            )

        return ret

    def run_setup(self, prev):
        """Run setup to set up the precondition"""
        return self.setup(prev)

    def add_precondition(self, precondition: Callable):
        """Add a precondition to the test case"""
        self.preconditions.append(precondition)

    def __str__(self) -> str:
        return self.name

    def to_dict(self) -> dict:
        """serialize to dict"""
        ret = {
            "precondition": list(map(lambda x: x.__name__, self.preconditions)),
            "mutator": self.mutator.__name__,
        }
        return ret


class K8sTestCase(TestCase):
    """Class represent a test case for k8s, purely for test case name purposes"""

    def __init__(
        self,
        precondition: Callable,
        mutator: Callable,
        setup: Callable,
        store: Optional[Store] = None,
    ) -> None:
        name = f"k8s-{mutator.__name__}"
        super().__init__(name, precondition, mutator, setup, store)


class K8sInvalidTestCase(K8sTestCase):
    """Class represent a test case for k8s, purely for test case name purposes"""

    def __init__(
        self,
        precondition: Callable,
        mutator: Callable,
        setup: Callable,
        store: Store = None,
    ) -> None:
        super().__init__(precondition, mutator, setup, store)


class EnumTestCase(TestCase):
    """Class represent a test case for enum fields"""

    def __init__(
        self,
        case,
        primitive: bool = False,
    ) -> None:
        self.case = case
        super().__init__(
            case, self.enum_precondition, self.enum_mutator, self.enum_setup
        )

    @staticmethod
    def enum_precondition(_):
        """Always true"""
        return True

    def enum_mutator(self, _):
        """Always return the case"""
        return self.case

    @staticmethod
    def enum_setup(_):
        """Never going to be called"""
        # FIXME: assert happens for rabbitmq's service.type field
        assert ()


class SchemaPrecondition:
    """Precondition for schema validation"""

    # XXX: Probably could use partial

    def __init__(self, schema) -> None:
        self.schema = schema

    def precondition(self, prev):
        """Precondition for schema validation"""
        return self.schema.validate(prev)
