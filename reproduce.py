import argparse
from functools import partial
import json
import logging
import subprocess
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

def apply_repro_testcase(value_with_schema: ValueWithSchema,
                   testcase: TestCase) -> jsonpatch.JsonPatch:
    logger = get_thread_logger(with_prefix=True)
    next_cr = testcase.mutator(None)  # next cr in yaml format

    prev = value_with_schema.raw_value()
    value_with_schema.update(next_cr)
    curr = value_with_schema.raw_value()
    logging.debug('current cr: %s', curr)

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Deploys operator with the seed CR')
    parser.add_argument('--seed',
                        '-s',
                        dest='seed',
                        required=True,
                        help="seed CR file")
    parser.add_argument('--operator',
                        '-o',
                        dest='operator',
                        required=False,
                        help="yaml file for deploying the operator")
    parser.add_argument('--helm',
                        dest='operator_chart',
                        required=False,
                        help='Path of operator helm chart')
    parser.add_argument('--kustomize',
                        dest='kustomize',
                        required=False,
                        help='Path of folder with kustomize')
    parser.add_argument('--init',
                        dest='init',
                        required=False,
                        help='Path of init yaml file (deploy before operator)')
    parser.add_argument('--context', dest='context', help='Cached context data')

    args = parser.parse_args()

    if args.operator_chart:
        deploy = Deploy(DeployMethod.HELM, args.operator_chart, args.init).new()
    elif args.operator:
        deploy = Deploy(DeployMethod.YAML, args.operator, args.init).new()
    elif args.kustomize:
        deploy = Deploy(DeployMethod.KUSTOMIZE, args.kustomize, args.init).new()
    else:
        raise UnknownDeployMethodError()

    construct_kind_cluster('test', CONST.K8S_VERSION)
    with open(args.context, 'r') as context_fin:
        context = json.load(context_fin)
        context['preload_images'] = set(context['preload_images'])
    # kind_load_images(context['preload_images'], 'test') # FIXME the first parameter is not a str, while it is expected to be
    deployed = deploy.deploy_with_retry(context, 'test')

    cmd = ['kubectl', 'apply', '-f', args.seed, '-n', context['namespace']]
    subprocess.run(cmd)
    kubectl(['apply', '-f', args.seed, '-n', context['namespace']], 'test')
