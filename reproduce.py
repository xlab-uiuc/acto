import argparse
import datetime
from functools import partial
import json
import sys
from logging import Logger
from types import SimpleNamespace
import jsonpatch
import yaml
from glob import glob
import os
from schema import BaseSchema, OpaqueSchema
from testplan import TreeNode

from value_with_schema import ValueWithSchema
from test_case import TestCase
from common import get_thread_logger
from input import InputModel
from acto import Acto

def apply_repro_testcase(value_with_schema: ValueWithSchema,
                   testcase: TestCase) -> jsonpatch.JsonPatch:
    logger = get_thread_logger(with_prefix=True)
    next_cr = testcase.mutator(None)  # next cr in yaml format

    prev = value_with_schema.raw_value()
    value_with_schema.update(next_cr)
    curr = value_with_schema.raw_value()
    logger.debug('current cr: %s', curr)

    patch = jsonpatch.make_patch(prev, curr)
    logger.info('JSON patch: %s' % patch)
    return patch

def load_cr_from_trial(trial_dir: str) -> list:
    '''Load mutated CRs from a trial directory
        Returns:
            list: list of mutated CRs
    '''
    cr_list = []
    for mutated_file in sorted(glob(os.path.join(trial_dir, 'mutated-*.yaml'))):
        with open(mutated_file, 'r') as f:
            cr_list.append(yaml.load(f, Loader=yaml.FullLoader))
    return cr_list

class CustomField:

    def __init__(self, path, schema) -> None:
        self.path = path
        self.custom_schema = schema

class ReproInputModel(InputModel):
    def __init__(self, trial_dir: str) -> None:
        self.root_schema = OpaqueSchema([], {})
        self.testcases = []
        cr_list = load_cr_from_trial(trial_dir)
        self.seed_input = cr_list[0]
        for cr in cr_list[1:]:
            cr_mutator = partial(repro_mutator, cr)
            t = TestCase(repro_precondition, cr_mutator, repro_setup)
            self.testcases.append(t)
            
    def initialize(self, initial_value: dict):
        pass
    
    def set_worker_id(self, id: int):
        pass
    
    def is_empty(self):
        '''If testcases are empty'''
        return len(self.testcases) == 0
    
    def get_seed_input(self) -> dict:
        return self.seed_input
    
    def next_test(self) -> list:
        '''
        Returns:
            - a list of tuples, containing
              an empty TreeNode and a test case
        '''
        return [tuple([TreeNode([]), self.testcases.pop(0)])] # return the first test case
    
    # def get_schema_by_path(self, path: list) -> BaseSchema:
    #     return BaseSchema()
    
    # def get_all_schemas(self):
    #     return []
    
    # def get_root_schema(self) -> BaseSchema:
    #     return self.root_schema
    
    def get_discarded_tests(self) -> dict:
        return {}
    
    def generate_test_plan(self) -> dict:
        return {}

    def apply_custom_field(self, custom_field: CustomField):
        pass
    
    def apply_default_value(self, default_value_result: dict):
        pass
    ## Some other methods of InputModel
    


def repro_precondition(v):
    return True

def repro_mutator(cr, v):
    return cr

def repro_setup(v):
    return None

# TODO add main function
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reproduce-dir',
                        dest='reproduce_dir',
                        required=True,
                        help='The directory of the trial folder to reproduce')
    parser.add_argument('--config', '-c', dest='config',
                        help='Operator port config path')
    args = parser.parse_args()
    with open(args.config, 'r') as config_file:
        config = json.load(config_file, object_hook=lambda d: SimpleNamespace(**d))
    if args.context == None:
        context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')
    else:
        context_cache = args.context
    Logger.info('Acto started with [%s]' % sys.argv)
    Logger.info('Operator config: %s', config)
    workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')
    start_time = datetime.now()
    acto = Acto(workdir_path, config, context_cache,
                 num_workers=1, is_reproduce=True, reproduce_dir=args.reproduce_dir)
    
    acto.run()
    end_time = datetime.now()
    Logger.info('Acto finished in %s', end_time - start_time)