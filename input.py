from functools import reduce
import json
import logging
import operator
import random
from typing import Tuple
from deepdiff import DeepDiff

from schema import extract_schema, BaseSchema
from value_with_schema import attach_schema_to_value


class CustomField:

    def __init__(self, path, schema) -> None:
        self.path = path
        self.custom_schema = schema


class InputModel:

    def __init__(self, crd: dict, mount: list = None) -> None:
        self.mount = ['spec']  # We model the cr.spec as the input
        self.root_schema = extract_schema(
            [], crd['spec']['versions'][0]['schema']['openAPIV3Schema'])
        self.seed_input = None
        self.current_input = None
        self.previous_input = None
        self.test_plan = None

        self.curr_field = None

    def initialize(self, initial_value: dict):
        self.seed_input = attach_schema_to_value(initial_value,
                                                 self.root_schema)
        self.current_input = attach_schema_to_value(initial_value,
                                                 self.root_schema)
        self.previous_input = attach_schema_to_value(initial_value,
                                                 self.root_schema)

    def reset_input(self):
        self.current_input = attach_schema_to_value(self.seed_input.raw_value(),
                                                 self.root_schema)
        self.previous_input = attach_schema_to_value(self.seed_input.raw_value(),
                                                 self.root_schema)

    def get_seed_input(self) -> dict:
        '''Get the raw value of the seed input'''
        return self.seed_input.raw_value()

    def get_schema_by_path(self, path: list) -> BaseSchema:
        return reduce(operator.getitem, path, self.root_schema)

    def get_all_schemas(self):
        '''Get all the schemas as a list'''
        return self.root_schema.get_all_schemas()

    def generate_test_plan(self):
        '''Generate test plan based on CRD'''
        ret = {}
        mounted_schema = self.get_schema_by_path(self.mount)
        schema_list = mounted_schema.get_all_schemas()
        num_fields = len(schema_list)
        num_testcases = 0
        for schema in schema_list:
            testcases = schema.test_cases()
            ret[json.dumps(schema.path).replace('\"ITEM\"', '0')] = testcases
            num_testcases += len(testcases)
        logging.info('Parsed [%d] fields from schema', num_fields)
        logging.info('Generated [%d] test cases in total', num_testcases)
        self.test_plan = ret
        return ret

    def next_test(self) -> Tuple[dict, bool]:
        '''Selects next test case to run from the test plan
        
        Randomly select a test field, and fetch the tail of the test case list
        Check if the precondition of the test case satisfies, if not, try to
        set up for the test case this time
        
        Returns:
            Tuple of (new value, if this is a setup)
        '''
        logging.info('Progress [%d] cases left' % sum([len(i) for i in self.test_plan.values()]))
        field = random.choice(list(self.test_plan.keys()))
        self.curr_field = field
        if len(self.test_plan[field]) == 0:
            del self.test_plan[field]
        test_case = self.test_plan[field][-1]
        curr = self.current_input.get_value_by_path(json.loads(field))
        logging.info('Selected field %s Previous value %s' % (field, curr))
        logging.info('Selected test [%s]' % test_case)
        if test_case.test_precondition(curr):
            setup = False
            next_value = test_case.mutator(curr)
            self.test_plan[field].pop()
            if len(self.test_plan[field]) == 0:
                del self.test_plan[field]
        else:
            setup = True
            next_value = test_case.run_setup(curr)
            logging.info('Precondition not satisfied, try setup')
        logging.debug('Next value: %s' % next_value)
        logging.debug(json.loads(field))

        # Save previous input
        self.previous_input = attach_schema_to_value(
            self.current_input.raw_value(), self.root_schema)

        # Create the path if not exist, then change the value
        self.current_input.create_path(json.loads(field))
        self.current_input.set_value_by_path(next_value, json.loads(field))
        return self.current_input.raw_value(), setup

    def get_input_delta(self):
        '''Compare the current input with the previous input
        
        Returns
            a delta object in tree view
        '''
        cr_diff = DeepDiff(self.previous_input.raw_value(),
                           self.current_input.raw_value(),
                           ignore_order=True,
                           report_repetition=True,
                           view='tree')
        return cr_diff

    def discard_test_case(self):
        '''Discard the test case that was selected'''
        discarded_case = self.test_plan[self.curr_field].pop()
        logging.info('Setup failed due to invalid, discard this testcase %s' %
                     discarded_case)
        if len(self.test_plan[self.curr_field]) == 0:
            del self.test_plan[self.curr_field]

    def revert(self):
        '''Revert back to previous input'''
        if self.previous_input == None:
            logging.error('No previous input to revert to')
        self.current_input = self.previous_input
        self.previous_input = None

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
