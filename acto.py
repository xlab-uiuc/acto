import argparse
import os
import kubernetes
import yaml
import time
from typing import Tuple
import random
from datetime import datetime
from copy import deepcopy
import signal
import logging
from deepdiff import DeepDiff
import importlib

from common import *
import check_result
from exception import UnknownDeployMethodError
from preprocess import add_acto_label, preload_images, process_crd
from input import InputModel
from deploy import Deploy, DeployMethod

test_summary = {}
workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')


def construct_kind_cluster():
    '''Delete kind cluster then create a new one
    '''
    os.system('kind delete cluster')

    kind_config_dir = 'kind_config'
    os.makedirs(kind_config_dir, exist_ok=True)
    kind_config_path = os.path.join(kind_config_dir, 'kind.yaml')

    with open(kind_config_path, 'w') as kind_config_file:
        kind_config_dict = {}
        kind_config_dict['kind'] = 'Cluster'
        kind_config_dict['apiVersion'] = 'kind.x-k8s.io/v1alpha4'
        kind_config_dict['nodes'] = []
        for _ in range(3):
            kind_config_dict['nodes'].append({'role': 'worker'})
        for _ in range(1):
            kind_config_dict['nodes'].append({'role': 'control-plane'})
        yaml.dump(kind_config_dict, kind_config_file)

    os.system('kind create cluster --config %s' % kind_config_path)

    kubernetes.config.load_kube_config()


def deploy_dependency(yaml_paths):
    logging.debug('Deploying dependencies')
    for yaml_path in yaml_paths:
        os.system('kubectl apply -f %s' % yaml_path)
    if len(yaml_paths) > 0:
        time.sleep(30)  # TODO: how to wait smartly
    return


def construct_candidate_helper(node, node_path, result: dict):
    '''Recursive helper to flatten the candidate dict

    Args:
        node: current node
        node_path: path to access this node from root
        result: output dict
    '''
    if 'candidates' in node:
        result[node_path] = node['candidates']
    else:
        for child_key, child_value in node.items():
            construct_candidate_helper(child_value,
                                       '%s.%s' % (node_path, child_key), result)


def construct_candidate_from_yaml(yaml_path: str) -> dict:
    '''Constructs candidate dict from a yaml file
    
    Args:
        yaml_path: path of the input yaml file
        
    Returns:
        dict[JSON-like path]: list of candidate values
    '''
    with open(yaml_path, 'r') as input_yaml:
        doc = yaml.load(input_yaml, Loader=yaml.FullLoader)
        result = {}
        construct_candidate_helper(doc, '', result)
        return result


def elect_mutation_parameter(candidates_dict: dict):
    '''method for electing the parameter to mutate and which value to pick
    
    Args:
        candidates_dict: flat dictionary specifying list of valid values for each parameter

    Returns:
        (path, value)
    '''
    random_entry = random.choice(list(candidates_dict.items()))
    return random_entry[0], random.choice(random_entry[1])


def mutate_application_spec(current_spec: dict, candidates: dict):
    '''mutate one of the fields in current spec according to candidates dict
    
    Args:
        current_spec: last spec that fed to operator
        candidates: flat dictionary specifying list of valid values for each parameter
    '''
    path, v = elect_mutation_parameter(candidates)
    logging.debug('Elected parameter [%s]' % path)
    logging.debug('Elected value: %s' % v)
    current_node = current_spec
    key_list = [x for x in path.split('.') if x]
    for key in key_list[:-1]:
        current_node = current_node[key]
    current_node[key_list[-1]] = v
    return current_spec


def prune_noneffective_change(diff):
    '''
    This helper function handles the corner case where an item is added to
    dictionary, but the value assigned is null, which makes the change 
    meaningless
    '''
    if 'dictionary_item_added' in diff:
        for item in diff['dictionary_item_added']:
            if item.t2 == None:
                diff['dictionary_item_added'].remove(item)
        if len(diff['dictionary_item_added']) == 0:
            del diff['dictionary_item_added']


def timeout_handler(sig, frame):
    raise TimeoutError


class Acto:

    def __init__(self, seed, deploy, crd_name, preload_images_,
                 custom_fields_src, context_file, dryrun) -> None:
        self.seed = seed
        self.deploy = deploy
        self.crd_name = crd_name
        self.dryrun = dryrun
        self.preload_images = []
        if preload_images_:
            self.preload_images.extend(preload_images_)
        self.curr_trial = 0

        if os.path.exists(context_file):
            with open(context_file, 'r') as context_fin:
                self.context = json.load(context_fin)
        else:
            # Some information needs to be fetched at runtime
            self.context = {
                'namespace': '',
                'current_dir_path': '',
                'crd': None
            }

            # Dummy run to automatically extract some information
            construct_kind_cluster()
            preload_images(self.preload_images)
            self.deploy.deploy(self.context)
            process_crd(self.context, self.crd_name)
            with open(context_file, 'w') as context_fout:
                json.dump(self.context, context_fout)

        # Apply custom fields
        self.input_model = InputModel(self.context['crd']['body'])
        self.input_model.initialize(self.seed)
        if custom_fields_src != None:
            module = importlib.import_module(custom_fields_src)
            for custom_field in module.custom_fields:
                self.input_model.apply_custom_field(custom_field)

        # Generate test cases
        self.test_plan = self.input_model.generate_test_plan()
        with open(os.path.join(workdir_path, 'test_plan.json'),
                  'w') as plan_file:
            json.dump(self.test_plan, plan_file, cls=ActoEncoder, indent=6)

    def run(self):
        while True:
            trial_start_time = time.time()
            construct_kind_cluster()
            preload_images(self.preload_images)
            self.deploy.deploy(self.context)
            add_acto_label(self.context)
            deploy_dependency([])
            trial_err, num_tests = self.run_trial(self.curr_trial)
            self.input_model.reset_input()

            trial_elapsed = time.strftime(
                "%H:%M:%S", time.gmtime(time.time() - trial_start_time))
            logging.info('Trial %d finished, completed in %s' %
                         (self.curr_trial, trial_elapsed))
            logging.info('---------------------------------------\n')

            result_dict = {}
            result_dict['trial_num'] = self.curr_trial
            result_dict['duration'] = trial_elapsed
            result_dict['num_tests'] = num_tests
            if trial_err == None:
                logging.info('Trial %d completed without error',
                             self.curr_trial)
            else:
                result_dict['oracle'] = trial_err.oracle
                result_dict['message'] = trial_err.message
                result_dict['input_delta'] = trial_err.input_delta
                result_dict['matched_system_delta'] = \
                    trial_err.matched_system_delta
            result_path = os.path.join(self.context['current_dir_path'],
                                       'result.json')
            with open(result_path, 'w') as result_file:
                json.dump(result_dict, result_file, cls=ActoEncoder, indent=6)
            self.curr_trial = self.curr_trial + 1

            if self.input_model.is_empty():
                logging.info('Test finished')
                break

    def run_trial(self,
                  trial_num: int,
                  num_mutation: int = 10) -> Tuple[ErrorResult, int]:
        '''Run a trial starting with the initial input, mutate with the candidate_dict, and mutate for num_mutation times
        
        Args:
            initial_input: the initial input without mutation
            candidate_dict: guides the mutation
            trial_num: how many trials have been run
            num_mutation: how many mutations to run at each trial
        '''
        trial_dir = os.path.join(workdir_path, 'trial-%04d' % trial_num)
        os.makedirs(trial_dir, exist_ok=True)
        self.context['current_dir_path'] = trial_dir

        checker = check_result.Checker(self.context, trial_dir)
        
        curr_input = self.input_model.get_seed_input()

        generation = 0
        while generation < num_mutation:
            setup = False
            if generation != 0:
                curr_input, setup = self.input_model.next_test()

            input_delta = self.input_model.get_input_delta()
            prune_noneffective_change(input_delta)
            if len(input_delta) == 0 and generation != 0:
                if setup:
                    logging.warning('Setup didn\'t change anything')
                    self.input_model.discard_test_case()
                logging.info('CR unchanged, continue')
                continue

            mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
            with open(mutated_filename, 'w') as mutated_cr_file:
                yaml.dump(curr_input, mutated_cr_file)

            cmd = [
                'kubectl', 'apply', '-f', mutated_filename, '-n',
                self.context['namespace']
            ]
            if not self.dryrun:
                result = checker.run_and_check(cmd,
                                               input_delta,
                                               generation=generation)
            else:
                result = PassResult()
            generation += 1

            if isinstance(result, InvalidInputResult):
                if setup:
                    self.input_model.discard_test_case()
                # Revert to parent CR
                self.input_model.revert()
            elif isinstance(result, UnchangedInputResult):
                if setup:
                    self.input_model.discard_test_case()
                continue
            elif isinstance(result, ErrorResult):
                # We found an error!
                if setup:
                    self.input_model.discard_test_case()
                return result, generation
            elif isinstance(result, PassResult):
                continue
            else:
                logging.error('Unknown return value, abort')
                quit()

        return None, generation


if __name__ == '__main__':
    start_time = time.time()

    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
    parser.add_argument('--candidates',
                        '-c',
                        dest='candidates',
                        required=True,
                        help="yaml file to specify candidates for parameters")
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
    parser.add_argument('--init',
                        dest='init',
                        required=False,
                        help='Path of init yaml file (deploy before operator)')
    parser.add_argument('--duration',
                        '-d',
                        dest='duration',
                        required=False,
                        help='Number of hours to run')
    parser.add_argument('--preload-images',
                        dest='preload_images',
                        nargs='*',
                        help='Docker images to preload into Kind cluster')
    parser.add_argument(
        '--crd-name',
        dest='crd_name',
        help='Name of CRD to use, required if there are multiple CRDs')
    parser.add_argument(
        '--custom-fields',
        dest='custom_fields',
        help='Python source file containing a list of custom fields')
    parser.add_argument('--context', dest='context', help='Cached context data')
    parser.add_argument('--dryrun',
                        dest='dryrun',
                        action='store_true',
                        help='Only generate test cases without executing them')

    args = parser.parse_args()

    os.makedirs(workdir_path, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format=
        '%(asctime)s %(levelname)-6s, %(name)s, %(filename)s:%(lineno)d, %(message)s'
    )
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    candidate_dict = construct_candidate_from_yaml(args.candidates)
    logging.debug(candidate_dict)

    application_cr: dict
    try:
        with open(args.seed, 'r') as cr_file:
            application_cr = yaml.load(cr_file, Loader=yaml.FullLoader)
    except:
        logging.error('Failed to read cr yaml, aborting')
        quit()

    # Preload frequently used images to amid ImagePullBackOff
    if args.preload_images:
        logging.info('%s will be preloaded into Kind cluster',
                     args.preload_images)

    # register timeout to automatically stop after # hours
    if args.duration != None:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(args.duration) * 60 * 60)

    if args.operator_chart:
        deploy = Deploy(DeployMethod.HELM, args.operator_chart, args.init).new()
    elif args.operator:
        deploy = Deploy(DeployMethod.YAML, args.operator, args.init).new()
    else:
        raise UnknownDeployMethodError()

    if args.context == None:
        context_cache = os.path.join(os.path.dirname(args.seed), 'context.json')
    else:
        context_cache = args.context

    acto = Acto(application_cr, deploy, args.crd_name, args.preload_images,
                args.custom_fields, context_cache, args.dryrun)
    acto.run()