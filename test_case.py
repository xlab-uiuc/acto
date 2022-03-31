from typing import Callable


class TestCase:

    def __init__(self,
                 precondition: Callable,
                 mutation: Callable,
                 setup: Callable,
                 additional_preconditions=[]) -> None:
        '''Class represent a test case

        Args:
            precondition: a function returns whether the previous value 
                satisfies the test case's precondition
            mutation: a function to change the value to execute the test case
            setup: a function to setup the precondition if the precondition 
                fails, so that we can run this test case next time
            additional_preconditions: additional precondition callbacks, this
                field is mainly used for AnyOfSchema
        '''

        self.precondition = precondition
        self.mutation = mutation
        self.setup = setup
        self.additional_preconditions = additional_preconditions

    def test_precondition(self, prev) -> bool:
        ret = self.precondition(prev)
        for additional_precondition in self.additional_preconditions:
            ret = ret and additional_precondition(prev)
        return ret

    def run_setup(self, prev):
        return self.setup(prev)

    def __str__(self) -> str:
        return self.mutation.__name__


class EnumTestCase(TestCase):

    def __init__(self, case) -> None:
        self.case = case
        super().__init__(self.enum_precondition, self.enum_mutation, self.setup)

    def enum_precondition(self, prev):
        return True

    def enum_mutation(self, prev):
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