import argparse
from datetime import datetime
from functools import partial
import json
import sys
import logging
import jsonpatch
import yaml
from glob import glob
import os

from acto.input.valuegenerator import extract_schema_with_value_generator

from acto.schema import BaseSchema, OpaqueSchema
from acto.input.testplan import TestGroup, TreeNode

from acto.input.value_with_schema import ValueWithSchema
from acto.input import TestCase
from acto.utils import OperatorConfig, get_thread_logger
from acto.input import InputModel
from acto_main import Acto


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

    def __init__(self,
                 crd: dict,
                 used_fields: list,
                 example_dir: str,
                 num_workers: int,
                 num_cases: int,
                 reproduce_dir: str,
                 mount: list = None) -> None:
        logger = get_thread_logger(with_prefix=True)
        # WARNING: Not sure the initialization is correct
        # TODO: The line below need to be reviewed.
        self.root_schema = extract_schema_with_value_generator([],
                                          crd['spec']['versions'][-1]['schema']['openAPIV3Schema'])
        self.testcases = []
        cr_list = load_cr_from_trial(reproduce_dir)
        if cr_list == []:
            raise Exception('No CRs found in %s. CR file name should start with mutated-' %
                            reproduce_dir)

        step = 1
        self.seed_input = cr_list[0]
        for cr in cr_list[1:]:
            cr_mutator = partial(repro_mutator, cr)
            t = TestCase(f'step-{step}', repro_precondition, cr_mutator, repro_setup)
            self.testcases.append(t)
            step += 1
        logger.info(f'{len(self.testcases)} steps for reproducing')
        self.num_total_cases = len(cr_list) - 1
        self.num_workers = 1
        self.metadata = {}

    def initialize(self, initial_value: dict):
        pass

    def set_worker_id(self, id: int):
        pass

    def set_mode(self, mode: str):
        pass

    def is_empty(self):
        '''If testcases are empty'''
        logger = get_thread_logger(with_prefix=True)
        logger.debug('testcases: %d' % len(self.testcases))
        return len(self.testcases) == 0

    def get_seed_input(self) -> dict:
        return self.seed_input

    def generate_test_plan(self, delta_from: str = None, focus_fields: list = None) -> dict:
        return {}

    def next_test(self) -> list:
        '''
        Returns:
            - a list of tuples, containing
              an empty TreeNode and a test case
        '''
        test = self.testcases.pop(0)
        return [(TestGroup([test]), ("[\"spec\"]", test))]  # return the first test case

    def apply_k8s_schema(self, k8s_field):
        pass

    def apply_custom_field(self, custom_field: CustomField):
        pass


def repro_precondition(v):
    return True


def repro_mutator(cr, v):
    return cr


def repro_setup(v):
    return None


def reproduce(workdir_path: str, reproduce_dir: str, operator_config: OperatorConfig, **kwargs):

    with open(operator_config, 'r') as config_file:
        config = OperatorConfig(**json.load(config_file))
    context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')
    input_model = ReproInputModel
    apply_testcase_f = apply_repro_testcase

    acto = Acto(workdir_path=workdir_path,
                operator_config=config,
                cluster_runtime=kwargs['cluster_runtime'],
                enable_analysis=True,
                preload_images_=None,
                context_file=context_cache,
                helper_crd=None,
                num_workers=1,
                num_cases=1,
                dryrun=False,
                analysis_only=False,
                is_reproduce=is_reproduce,
                input_model=input_model,
                apply_testcase_f=apply_testcase_f,
                reproduce_dir=reproduce_dir)

    acto.run(modes=['normal'])


# TODO add main function
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
    parser.add_argument(
        '--reproduce-dir',
        dest='reproduce_dir',
        required=True,
        help=
        'The directory of the trial folder to reproduce. CR files should have names starting with "mutated-"'
    )
    parser.add_argument('--config', '-c', dest='config', help='Operator port config path')
    parser.add_argument(
        '--cluster-runtime',
        '-r',
        dest='cluster_runtime',
        default="KIND",
        help='Cluster runtime for kubernetes, can be KIND (Default), K3D or MINIKUBE')
    parser.add_argument('--context', dest='context', help='Cached context data')
    args = parser.parse_args()

    workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')
    os.makedirs(workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    logger = get_thread_logger(with_prefix=False)

    is_reproduce = True
    start_time = datetime.now()
    reproduce(workdir_path=workdir_path,
              reproduce_dir=args.reproduce_dir,
              operator_config=args.config,
              cluster_runtime=args.cluster_runtime)
    end_time = datetime.now()
    logger.info('Acto finished in %s', end_time - start_time)