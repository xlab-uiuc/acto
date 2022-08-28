from functools import reduce
import json
import logging
import math
import operator
import random
import threading
from typing import Tuple
from deepdiff import DeepDiff
import glob
import yaml

from schema import extract_schema, BaseSchema, ObjectSchema, ArraySchema
from testplan import TestPlan
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


class ProblematicField(CustomField):
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

    def __init__(self, crd: dict, example_dir: str, num_workers: int, num_cases: int, mount: list = None) -> None:
        if mount != None:
            self.mount = mount
        else:
            self.mount = ['spec']  # We model the cr.spec as the input
        self.root_schema = extract_schema([],
                                          crd['spec']['versions'][-1]['schema']['openAPIV3Schema'])

        # Load all example documents
        self.example_dir = example_dir
        example_docs = []
        for example_filepath in glob.glob(example_dir + '*.yaml'):
            with open(example_filepath, 'r') as example_file:
                docs = yaml.load_all(example_file, Loader=yaml.FullLoader)
                for doc in docs:
                    example_docs.append(doc)

        for example_doc in example_docs:
            self.root_schema.load_examples(example_doc)

        self.num_workers = num_workers
        self.num_cases = num_cases
        self.seed_input = None
        self.test_plan_partitioned = None
        self.thread_vars = threading.local()

    def initialize(self, initial_value: dict):
        initial_value['metadata']['name'] = 'test-cluster'
        self.initial_value = initial_value
        self.seed_input = attach_schema_to_value(initial_value, self.root_schema)

    def set_worker_id(self, id: int):
        '''Claim this thread's id, so that we can split the test plan among threads'''
        # Thread local variables
        self.thread_vars.id = id
        # so that we can run the test case itself right after the setup
        self.thread_vars.test_plan = TestPlan(self.root_schema.to_tree())

        for key, value in dict(self.test_plan_partitioned[id]).items():
            path = json.loads(key)
            self.thread_vars.test_plan.add_testcases_by_path(value, path)

    def is_empty(self):
        '''if test plan is empty'''
        return len(self.thread_vars.test_plan) == 0

    def get_seed_input(self) -> dict:
        '''Get the raw value of the seed input'''
        return self.seed_input.raw_value()

    def get_schema_by_path(self, path: list) -> BaseSchema:
        return reduce(operator.getitem, path, self.root_schema)

    def get_all_schemas(self):
        '''Get all the schemas as a list'''
        return self.root_schema.get_all_schemas()

    def get_root_schema(self) -> BaseSchema:
        return self.root_schema

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
        random.shuffle(test_plan_items)  # randomize to reduce skewness among workers
        chunk_size = math.ceil(len(test_plan_items) / self.num_workers)
        self.test_plan_partitioned = []
        for i in range(0, len(test_plan_items), chunk_size):
            self.test_plan_partitioned.append(test_plan_items[i:i + chunk_size])
        # appending empty lists to avoid no test cases distributed to certain work nodes
        if len(test_plan_items) < self.num_workers:
            for i in range(self.num_workers - len(test_plan_items)):
                self.test_plan_partitioned.append([])
        assert (self.num_workers == len(self.test_plan_partitioned))

        return ret

    def next_test(self) -> list:
        '''Selects next test case to run from the test plan
        
        Randomly select a test field, and fetch the tail of the test case list
        Check if the precondition of the test case satisfies, if not, try to
        set up for the test case this time
        
        Returns:
            Tuple of (new value, if this is a setup)
        '''
        logging.info('Progress [%d] cases left' % len(self.thread_vars.test_plan))

        ret = []

        # TODO: multi-testcase
        selected_fields = self.thread_vars.test_plan.select_fields(num_cases=self.num_cases)

        for selected_field in selected_fields:
            logging.info('Selected field [%s]', selected_field.get_path())
            ret.append(tuple([selected_field, selected_field.get_next_testcase()]))

        return ret

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
