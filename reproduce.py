import argparse
from datetime import datetime
from functools import partial
import json
import sys
import logging
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
                         path: list,
                         testcase: TestCase,
                         setup: bool = False) -> jsonpatch.JsonPatch:
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
    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
    parser.add_argument('--reproduce-dir',
                        dest='reproduce_dir',
                        required=True,
                        help='The directory of the trial folder to reproduce')
    parser.add_argument('--config', '-c', dest='config',
                        help='Operator port config path')
    parser.add_argument('--cluster-runtime', '-r', dest='cluster_runtime',
                        default="KIND",
                        help='Cluster runtime for kubernetes, can be KIND (Default), K3D or MINIKUBE')
    parser.add_argument('--enable-analysis',
                        dest='enable_analysis',
                        action='store_true',
                        help='Enables static analysis to prune false alarms')
    parser.add_argument('--duration',
                        '-d',
                        dest='duration',
                        required=False,
                        help='Number of hours to run')
    parser.add_argument('--preload-images',
                        dest='preload_images',
                        nargs='*',
                        help='Docker images to preload into Kind cluster')
    # Temporary solution before integrating controller-gen
    parser.add_argument('--helper-crd',
                        dest='helper_crd',
                        help='generated CRD file that helps with the input generation')
    parser.add_argument('--context', dest='context', help='Cached context data')
    parser.add_argument('--num-workers',
                        dest='num_workers',
                        type=int,
                        default=1,
                        help='Number of concurrent workers to run Acto with')
    parser.add_argument('--num-cases',
                        dest='num_cases',
                        type=int,
                        default=1,
                        help='Number of testcases to bundle each time')
    parser.add_argument('--learn', dest='learn', action='store_true', help='Learn mode')
    parser.add_argument('--notify-crash',
                        dest='notify_crash',
                        action='store_true',
                        help='Submit a google form response to notify')
    parser.add_argument('--learn-analysis', dest='learn_analysis_only', action='store_true', 
                        help='Only learn analysis')
    parser.add_argument('--dryrun',
                        dest='dryrun',
                        action='store_true',
                        help='Only generate test cases without executing them')
    args = parser.parse_args()
    
    workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')
    os.makedirs(workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format=
        '%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s'
    )
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    logger = get_thread_logger(with_prefix=False)
    
    with open(args.config, 'r') as config_file:
        config = json.load(config_file, object_hook=lambda d: SimpleNamespace(**d))
    context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')
    logger.info('Acto started with [%s]' % sys.argv)
    logger.info('Operator config: %s', config)
    
    input_model = ReproInputModel(args.reproduce_dir)
    apply_testcase_f = apply_repro_testcase
    is_reproduce = True
    start_time = datetime.now()
    acto = Acto(workdir_path, config, args.cluster_runtime, args.enable_analysis, args.preload_images, context_cache,
                args.helper_crd, args.num_workers, args.num_cases, args.dryrun, args.learn_analysis_only, is_reproduce, input_model, apply_testcase_f)
    
    acto.run()
    end_time = datetime.now()
    logger.info('Acto finished in %s', end_time - start_time)