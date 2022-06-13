from functools import reduce
import json
import logging
import math
import operator
import random
import threading
from typing import Tuple
from deepdiff import DeepDiff

from schema import extract_schema, BaseSchema, ObjectSchema, ArraySchema
from value_with_schema import attach_schema_to_value
from common import random_string


class CustomField:

    def __init__(self, path, schema) -> None:
        self.path = path
        self.custom_schema = schema


class CopiedOverField(CustomField):
    '''For pruning the fields that are simply copied over to other resources
    
    All the subfields of this field (excluding this field) will be pruned
    '''

    class PruneChildrenObjectSchema(ObjectSchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema) -> None:
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            '''Return all the subschemas as a list'''
            return [self]

        def __str__(self) -> str:
            return 'Children Pruned'

    class PruneChildrenArraySchema(ArraySchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema) -> None:
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            '''Return all the subschemas as a list'''
            return [self]

        def __str__(self) -> str:
            return 'Children Pruned'

    def __init__(self, path, array: bool = False) -> None:
        if array:
            super().__init__(path, self.PruneChildrenArraySchema)
        else:
            super().__init__(path, self.PruneChildrenObjectSchema)


class ProblemMaticField(CustomField):
    '''For pruning the field that can not be simply generated using Acto's current generation mechanism.
    
    All the subfields of this field (including this field itself) will be pruned
    '''

    class PruneEntireObjectSchema(ObjectSchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema) -> None:
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            return []

        def __str__(self):
            return "Field Pruned"

    class PruneEntireArraySchema(ArraySchema):

        def __init__(self, path: list, schema: dict) -> None:
            super().__init__(path, schema)

        def __init__(self, schema_obj: BaseSchema) -> None:
            super().__init__(schema_obj.path, schema_obj.raw_schema)

        def get_all_schemas(self) -> list:
            return []

        def __str__(self):
            return "Field Pruned"

    def __init__(self, path, array: bool = False) -> None:
        if array:
            super().__init__(path, self.PruneEntireArraySchema)
        else:
            super().__init__(path, self.PruneEntireObjectSchema)


class InputModel:

    def __init__(self, crd: dict, num_workers: int, mount: list = None) -> None:
        if mount != None:
            self.mount = mount
        else:
            self.mount = ['spec']  # We model the cr.spec as the input
        self.root_schema = extract_schema([],
                                          crd['spec']['versions'][-1]['schema']['openAPIV3Schema'])
        self.num_workers = num_workers
        self.seed_input = None
        self.test_plan_partitioned = None
        self.discarded_tests = {}  # List of test cases failed to run
        self.thread_vars = threading.local()


    def initialize(self, initial_value: dict):
        initial_value['metadata']['name'] = 'test-cluster'
        self.initial_value = initial_value
        self.seed_input = attach_schema_to_value(initial_value,
                                                 self.root_schema)

    def set_worker_id(self, id: int):
        '''Claim this thread's id, so that we can split the test plan among threads'''
        # Thread local variables
        self.thread_vars.id = id
        self.thread_vars.curr_field = None  # Bookkeeping in case we are running setup
        # so that we can run the test case itself right after the setup
        self.thread_vars.test_plan = dict(self.test_plan_partitioned[id])

        self.thread_vars.current_input = attach_schema_to_value(
            self.initial_value, self.root_schema)
        self.thread_vars.previous_input = attach_schema_to_value(
            self.initial_value, self.root_schema)

    def is_empty(self):
        '''if test plan is empty'''
        return len(self.thread_vars.test_plan) == 0

    def reset_input(self):
        '''Reset the current input back to seed'''
        self.thread_vars.current_input = attach_schema_to_value(self.seed_input.raw_value(), self.root_schema)
        self.thread_vars.previous_input = attach_schema_to_value(self.seed_input.raw_value(), self.root_schema)

    def get_seed_input(self) -> dict:
        '''Get the raw value of the seed input'''
        return self.seed_input.raw_value()

    def get_schema_by_path(self, path: list) -> BaseSchema:
        return reduce(operator.getitem, path, self.root_schema)

    def get_all_schemas(self):
        '''Get all the schemas as a list'''
        return self.root_schema.get_all_schemas()

    def get_discarded_tests(self) -> dict:
        return self.discarded_tests

    def generate_test_plan(self):
        '''Generate test plan based on CRD'''
        ret = {}
        mounted_schema = self.get_schema_by_path(self.mount)
        schema_list = mounted_schema.get_all_schemas()
        num_fields = len(schema_list)
        num_testcases = 0
        for schema in schema_list:
            testcases = schema.test_cases()
            path = json.dumps(schema.path).replace('\"ITEM\"',
                                                   '0').replace('additional_properties',
                                                                random_string(5))
            ret[path] = testcases
            num_testcases += len(testcases)
        logging.info('Parsed [%d] fields from schema', num_fields)
        logging.info('Generated [%d] test cases in total', num_testcases)
        self.test_plan = ret

        test_plan_items = list(self.test_plan.items())
        chunk_size = math.ceil(len(test_plan_items) / self.num_workers)
        self.test_plan_partitioned = []
        for i in range(0, len(test_plan_items), chunk_size):
            self.test_plan_partitioned.append(test_plan_items[i:i + chunk_size])
        assert (self.num_workers == len(self.test_plan_partitioned))

        return ret

    def curr_test(self) -> Tuple[dict, bool]:
        return self.thread_vars.current_input.raw_value(), self.thread_vars.current_input_setup

    def next_test(self) -> Tuple[dict, bool]:
        '''Selects next test case to run from the test plan
        
        Randomly select a test field, and fetch the tail of the test case list
        Check if the precondition of the test case satisfies, if not, try to
        set up for the test case this time
        
        Returns:
            Tuple of (new value, if this is a setup)
        '''
        logging.info('Progress [%d] cases left' %
                     sum([len(i) for i in self.thread_vars.test_plan.values()]))
        if self.thread_vars.curr_field != None:
            field = self.thread_vars.curr_field
        else:
            field = random.choice(list(self.thread_vars.test_plan.keys()))
        self.thread_vars.curr_field = field
        test_case = self.thread_vars.test_plan[field][-1]
        logging.debug('field: %s' % field)
        curr = self.thread_vars.current_input.get_value_by_path(json.loads(field))
        logging.info('Selected field %s Previous value %s' % (field, curr))
        logging.info('Selected test [%s]' % test_case)

        # run test if precondition satisfies
        # run setup if precondition fails
        if test_case.test_precondition(curr):
            setup = False
            next_value = test_case.mutator(curr)
            self.thread_vars.test_plan[field].pop()
            if len(self.thread_vars.test_plan[field]) == 0:
                del self.thread_vars.test_plan[field]
            self.thread_vars.curr_field = None
        else:
            setup = True
            next_value = test_case.run_setup(curr)
            logging.info('Precondition not satisfied, try setup')
        logging.debug('Next value: %s' % next_value)
        logging.debug(json.loads(field))

        # Save previous input
        self.thread_vars.previous_input = attach_schema_to_value(
            self.thread_vars.current_input.raw_value(), self.root_schema)

        # Create the path if not exist, then change the value
        self.thread_vars.current_input.create_path(json.loads(field))
        self.thread_vars.current_input.set_value_by_path(next_value, json.loads(field))
        self.thread_vars.current_input_setup = setup
        return self.thread_vars.current_input.raw_value(), setup

    def get_input_delta(self):
        '''Compare the current input with the previous input
        
        Returns
            a delta object in tree view
        '''
        cr_diff = DeepDiff(self.thread_vars.previous_input.raw_value(),
                           self.thread_vars.current_input.raw_value(),
                           ignore_order=True,
                           report_repetition=True,
                           view='tree')
        return cr_diff

    def discard_test_case(self):
        '''Discard the test case that was selected'''
        discarded_case = self.thread_vars.test_plan[self.thread_vars.curr_field].pop()

        # Log it to discarded_tests
        if self.thread_vars.curr_field in self.discarded_tests:
            self.discarded_tests[self.thread_vars.curr_field].append(discarded_case)
        else:
            self.discarded_tests[self.thread_vars.curr_field] = [discarded_case]
        logging.info('Setup failed due to invalid, discard this testcase %s' % discarded_case)

        if len(self.thread_vars.test_plan[self.thread_vars.curr_field]) == 0:
            del self.thread_vars.test_plan[self.thread_vars.curr_field]
        self.thread_vars.curr_field = None

    def revert(self):
        '''Revert back to previous input'''
        # FIXME
        if self.thread_vars.previous_input == None:
            logging.error('No previous input to revert to')
        self.thread_vars.current_input = self.thread_vars.previous_input
        self.thread_vars.previous_input = None

    def apply_custom_field(self, custom_field: CustomField):
        '''Applies custom field to the input model
        
        Relies on the __setitem__ and __getitem__ methods of schema class
        '''
        path = custom_field.path
        if len(path) == 0:
            self.root_schema = custom_field.custom_schema(self.root_schema)

        # fetch the parent schema
        curr = self.root_schema
        for idx in path[:-1]:
            curr = curr[idx]

        # construct new schema
        custom_schema = custom_field.custom_schema(curr[path[-1]])

        # replace old schema with the new one
        curr[path[-1]] = custom_schema

    def apply_candidates(self, candidates: dict, path: list):
        '''Apply candidates file onto schema'''
        # TODO
        candidates_list = self.candidates_dict_to_list(candidates, path)

    def candidates_dict_to_list(self, candidates: dict, path: list) -> list:
        if 'candidates' in candidates:
            return [(path, candidates['candidates'])]
        else:
            ret = []
            for key, value in candidates.items():
                ret.extend(self.candidates_dict_to_list(value, path + [key]))
            return ret
