from typing import Callable

from thread_logger import get_thread_logger


class Store:

    def __init__(self) -> None:
        self.data = None


class TestCase:

    def __init__(self,
                 name: str,
                 precondition: Callable,
                 mutator: Callable,
                 setup: Callable,
                 store: Store = None) -> None:
        '''Class represent a test case

        Args:
            name: the name of the test case
            precondition: a function returns whether the previous value 
                satisfies the test case's precondition
            mutator: a function to change the value to execute the test case
            setup: a function to setup the precondition if the precondition 
                fails, so that we can run this test case next time
            additional_preconditions: additional precondition callbacks, this
                field is mainly used for AnyOfSchema
        '''

        self.name = name
        self.precondition = precondition
        self.mutator = mutator
        self.setup = setup
        self.additional_preconditions = []
        self.store = store

    def test_precondition(self, prev) -> bool:
        logger = get_thread_logger(with_prefix=True)

        ret = True
        for additional_precondition in self.additional_preconditions:
            ret = ret and additional_precondition(prev)
            logger.debug('Precondition [%s] Result [%s]' % (additional_precondition.__name__, ret))
        if self.store != None:
            ret = ret and self.precondition(prev, self.store)
        else:
            ret = ret and self.precondition(prev)
        logger.debug('Precondition [%s] Result [%s]' % (self.precondition.__name__, ret))
        return ret

    def run_setup(self, prev):
        return self.setup(prev)

    def add_precondition(self, precondition: callable):
        self.additional_preconditions.append(precondition)

    def __str__(self) -> str:
        return '%s' % (self.name)

    def to_dict(self) -> dict:
        ret = {}
        ret['precondition'] = self.precondition.__name__
        ret['mutator'] = self.mutator.__name__
        ret['additional_preconditions'] = len(self.additional_preconditions)
        # for additional_precondition in self.additional_preconditions:
        #     ret['additional_preconditions'].append(additional_precondition.__name__)
        return ret


class K8sTestCase(TestCase):
    '''Class represent a test case for k8s, purely for test case name purposes'''

    def __init__(self,
                 precondition: Callable,
                 mutator: Callable,
                 setup: Callable,
                 store: Store = None) -> None:
        name = 'k8s-%s' % (mutator.__name__)
        super().__init__(name, precondition, mutator, setup, store)


class EnumTestCase(TestCase):

    def __init__(self, case) -> None:
        self.case = case
        super().__init__(case, self.enum_precondition, self.enum_mutator, self.setup)

    def enum_precondition(self, prev):
        return True

    def enum_mutator(self, prev):
        return self.case

    def setup(self, prev):
        '''Never going to be called'''
        # FIXME: assert happens for rabbitmq's service.type field
        assert ()


class SchemaPrecondition:
    # XXX: Probably could use partial

    def __init__(self, schema) -> None:
        self.schema = schema

    def precondition(self, prev):
        return self.schema.validate(prev)