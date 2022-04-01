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

from common import *
import check_result
from exception import UnknownDeployMethodError
from preprocess import add_acto_label, preload_images, process_crd
import value_with_schema
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


def run_trial(initial_input: dict,
              candidate_dict: dict,
              trial_num: int,
              context: dict,
              test_plan: dict,
              num_mutation: int = 300) -> Tuple[ErrorResult, int]:
    '''Run a trial starting with the initial input, mutate with the candidate_dict, and mutate for num_mutation times
    
    Args:
        initial_input: the initial input without mutation
        candidate_dict: guides the mutation
        trial_num: how many trials have been run
        num_mutation: how many mutations to run at each trial
    '''
    trial_dir = os.path.join(workdir_path, str(trial_num))
    os.makedirs(trial_dir, exist_ok=True)
    context['current_dir_path'] = trial_dir

    checker = check_result.Checker(context, trial_dir)
    current_cr = deepcopy(initial_input)
    spec_with_schema = value_with_schema.attach_schema_to_value(
        current_cr['spec'], context['crd']['spec_schema'])

    generation = 0
    while generation < num_mutation:
        parent_cr = deepcopy(current_cr)
        if len(test_plan) == 0:
            logging.info('Finished all the test cases')
            break
        setup = False
        if generation != 0:
            field = random.choice(list(test_plan.keys()))
            test_case = test_plan[field][-1]
            prev_value = spec_with_schema.get_value_by_path(json.loads(field))
            logging.debug('Selected field %s Previous value %s' % (field, prev_value))
            if test_case.test_precondition(prev_value):
                next_value = test_case.mutator(prev_value)
                test_plan[field].pop()
                if len(test_plan[field]) == 0:
                    del test_plan[field]
            else:
                setup = True
                next_value = test_case.run_setup(prev_value)
                logging.info('Precondition not satisfied, try setup')
            logging.debug('Next value: %s' % next_value)
            logging.debug(json.loads(field))
            spec_with_schema.create_path(json.loads(field))
            spec_with_schema.set_value_by_path(next_value, json.loads(field))
            current_cr['spec'] = spec_with_schema.raw_value()

        cr_diff = DeepDiff(parent_cr,
                           current_cr,
                           ignore_order=True,
                           report_repetition=True,
                           view='tree')
        prune_noneffective_change(cr_diff)
        if len(cr_diff) == 0 and generation != 0:
            logging.info('CR unchanged, continue')
            continue

        mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump(current_cr, mutated_cr_file)

        cmd = [
            'kubectl', 'apply', '-f', mutated_filename, '-n',
            context['namespace']
        ]
        result = checker.run_and_check(cmd, cr_diff, generation=generation)
        generation += 1

        if isinstance(result, InvalidInputResult):
            if setup:
                logging.info('Setup failed due to invalid, discard this testcase %s' % test_case)
                test_plan[field].pop()
            # Revert to parent CR
            current_cr = parent_cr
            spec_with_schema = value_with_schema.attach_schema_to_value(
                current_cr['spec'], context['crd']['spec_schema'])
        elif isinstance(result, UnchangedInputResult):
            continue
        elif isinstance(result, ErrorResult):
            # We found an error!
            if setup:
                logging.info('Setup failed due to error, discard this testcase %s' % test_case)
                test_plan[field].pop()
            return result, generation
        elif isinstance(result, PassResult):
            continue
        else:
            logging.error('Unknown return value, abort')
            quit()

    return None, generation


def timeout_handler(sig, frame):
    raise TimeoutError


class Acto:

    def __init__(self, seed, deploy, crd_name, preload_images_) -> None:
        self.seed = seed
        self.deploy = deploy
        self.crd_name = crd_name
        self.preload_images = []
        if preload_images_:
            self.preload_images.extend(preload_images_)
        self.curr_trial = 0

        # Some information needs to be fetched at runtime
        self.context = {'namespace': '', 'current_dir_path': '', 'crd': None}

        # Dummy run to automatically extract some information
        # TODO: Save the result to data directory
        construct_kind_cluster()
        preload_images(self.preload_images)
        self.deploy.deploy(self.context)
        process_crd(self.context, self.crd_name)

        # Generate test cases
        schema_list = self.context['crd']['spec_schema'].get_all_schemas()
        self.test_plan = {}
        num_fields = len(schema_list)
        num_testcases = 0
        for schema in schema_list:
            testcases = schema.test_cases()
            self.test_plan[json.dumps(schema.path).replace('\"ITEM\"', '0')] = testcases
            num_testcases += len(testcases)
        logging.info('Parsed [%d] fields from schema', num_fields)
        logging.info('Generated [%d] test cases in total', num_testcases)
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
            trial_err, num_tests = run_trial(application_cr, candidate_dict,
                                             self.curr_trial, self.context,
                                             self.test_plan)

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
                logging.info('Trial %d completed without error', self.curr_trial)
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
                        default=6,
                        help='Number of hours to run')
    parser.add_argument('--preload-images',
                        dest='preload_images',
                        nargs='*',
                        help='Docker images to preload into Kind cluster')
    parser.add_argument(
        '--crd-name',
        dest='crd_name',
        help='Name of CRD to use, required if there are multiple CRDs')

    args = parser.parse_args()

    os.makedirs(workdir_path, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-6s, %(name)s, %(filename)s:%(lineno)d, %(message)s')
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
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(args.duration) * 60 * 60)

    if args.operator_chart:
        deploy = Deploy(DeployMethod.HELM, args.operator_chart, args.init).new()
    elif args.operator:
        deploy = Deploy(DeployMethod.YAML, args.operator, args.init).new()
    else:
        raise UnknownDeployMethodError()

    acto = Acto(application_cr, deploy, args.crd_name, args.preload_images)
    acto.run()