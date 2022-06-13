import argparse
import os
import sys
import threading
import kubernetes
import yaml
import time
from typing import Tuple
import random
from datetime import datetime
import signal
import logging
import importlib
import traceback

from common import *
import check_result
from exception import UnknownDeployMethodError
from preprocess import add_acto_label, process_crd, update_preload_images
from input import InputModel
from deploy import Deploy, DeployMethod
from constant import CONST
from runner import Runner
from check_result import Checker
from snapshot import EmptySnapshot

CONST = CONST()
random.seed(0)


def construct_kind_cluster(cluster_name: str, k8s_version: str):
    '''Delete kind cluster then create a new one

    Args:
        name: name of the k8s cluster
        k8s_version: version of k8s to use
    '''
    logging.info('Deleting kind cluster...')
    kind_delete_cluster(cluster_name)
    time.sleep(5)

    kind_config_dir = 'kind_config'
    os.makedirs(kind_config_dir, exist_ok=True)
    kind_config_path = os.path.join(kind_config_dir, 'kind.yaml')

    if not os.path.exists(kind_config_path):
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

    p = kind_create_cluster(cluster_name, kind_config_path, k8s_version)
    if p.returncode != 0:
        logging.error('Failed to create kind cluster, retrying')
        kind_delete_cluster(cluster_name)
        time.sleep(5)
        kind_create_cluster(cluster_name, kind_config_path, k8s_version)

    logging.info('Created kind cluster')

    kubernetes.config.load_kube_config(context=kind_kubecontext(cluster_name))


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
            construct_candidate_helper(child_value, '%s.%s' % (node_path, child_key), result)


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


class TrialRunner:

    def __init__(self, context: dict, input_model: InputModel, deploy: Deploy, workdir: str,
                 worker_id: int, dryrun: bool) -> None:
        self.context = context
        self.workdir = workdir
        self.worker_id = worker_id
        self.cluster_name = f"acto-cluster-{worker_id}"
        self.input_model = input_model
        self.deploy = deploy
        self.dryrun = dryrun

        self.snapshots = []

    def run(self):
        self.input_model.set_worker_id(self.worker_id)
        curr_trial = 0
        apiclient = None

        while True:
            trial_start_time = time.time()
            construct_kind_cluster(self.cluster_name, CONST.K8S_VERSION)
            apiclient = kubernetes_client(self.cluster_name)
            kind_load_images(self.context['preload_images'], self.cluster_name)
            deployed = self.deploy.deploy_with_retry(self.context, self.cluster_name)
            if not deployed:
                logging.info('Not deployed. Try again!')
                continue

            add_acto_label(apiclient, self.context)

            trial_dir = os.path.join(self.workdir, 'trial-%02d-%04d' % (self.worker_id, curr_trial))
            os.makedirs(trial_dir, exist_ok=True)

            trial_err, num_tests = self.run_trial(trial_dir=trial_dir)
            self.input_model.reset_input()
            self.snapshots = []

            trial_elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - trial_start_time))
            logging.info('Trial %d finished, completed in %s' % (curr_trial, trial_elapsed))
            logging.info('---------------------------------------\n')

            result_dict = {}
            result_dict['trial_num'] = curr_trial
            result_dict['duration'] = trial_elapsed
            result_dict['num_tests'] = num_tests
            if trial_err == None:
                logging.info('Trial %d completed without error', curr_trial)
            else:
                result_dict['oracle'] = trial_err.oracle
                result_dict['message'] = trial_err.message
                result_dict['input_delta'] = trial_err.input_delta
                result_dict['matched_system_delta'] = \
                    trial_err.matched_system_delta
            result_path = os.path.join(trial_dir, 'result.json')
            with open(result_path, 'w') as result_file:
                json.dump(result_dict, result_file, cls=ActoEncoder, indent=6)
            curr_trial = curr_trial + 1

            if self.input_model.is_empty():
                logging.info('Test finished')
                break

        logging.info('Failed test cases: %s' %
                     json.dumps(self.input_model.get_discarded_tests(), cls=ActoEncoder, indent=4))

    def run_trial(self, trial_dir: str, num_mutation: int = 10) -> Tuple[ErrorResult, int]:
        '''Run a trial starting with the initial input, mutate with the candidate_dict, and mutate for num_mutation times
        
        Args:
            initial_input: the initial input without mutation
            candidate_dict: guides the mutation
            trial_num: how many trials have been run
            num_mutation: how many mutations to run at each trial
        '''

        runner = Runner(self.context, trial_dir, self.cluster_name)
        checker = Checker(self.context, trial_dir)

        curr_input = self.input_model.get_seed_input()
        self.snapshots.append(EmptySnapshot(curr_input))

        generation = 0
        retry = False
        while generation < num_mutation:
            setup = False
            # if connection refused, feed the current test as input again
            if retry == True:
                curr_input, setup = self.input_model.curr_test()
                retry = False
            elif generation != 0:
                curr_input, setup = self.input_model.next_test()

            input_delta = self.input_model.get_input_delta()
            prune_noneffective_change(input_delta)
            if len(input_delta) == 0 and generation != 0:
                if setup:
                    logging.warning('Setup didn\'t change anything')
                    self.input_model.discard_test_case()
                logging.info('CR unchanged, continue')
                continue

            if not self.dryrun:
                snapshot = runner.run(curr_input, generation)
                result = checker.check(snapshot, self.snapshots[-1], generation)
                self.snapshots.append(snapshot)
                generation += 1
            else:
                result = PassResult()
                generation += 1

            if isinstance(result, ConnectionRefusedResult):
                # Connection refused due to webhook not ready, let's wait for a bit
                logging.info('Connection failed. Retry the test after 20 seconds')
                time.sleep(20)
                # retry
                retry = True
                continue
            if isinstance(result, InvalidInputResult):
                if setup:
                    self.input_model.discard_test_case()
                # Revert to parent CR
                self.input_model.revert()
                self.snapshots.pop()

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

            if self.input_model.is_empty():
                break

        return None, generation


class Acto:

    def __init__(self,
                 seed_file,
                 deploy: Deploy,
                 workdir_path,
                 crd_name,
                 preload_images_,
                 custom_fields_src,
                 helper_crd: str,
                 context_file: str,
                 num_workers: int,
                 dryrun: bool,
                 mount: list = None) -> None:
        try:
            with open(seed_file, 'r') as cr_file:
                self.seed = yaml.load(cr_file, Loader=yaml.FullLoader)
        except:
            logging.error('Failed to read seed yaml, aborting')
            quit()
        self.deploy = deploy
        self.crd_name = crd_name
        self.workdir_path = workdir_path
        self.num_workers = num_workers
        self.dryrun = dryrun
        self.snapshots = []

        if os.path.exists(context_file):
            with open(context_file, 'r') as context_fin:
                self.context = json.load(context_fin)
                self.context['preload_images'] = set(self.context['preload_images'])
        else:
            # Run learning run to collect some information from runtime
            logging.info('Starting learning run to collect information')
            self.context = {'namespace': '', 'crd': None, 'preload_images': set()}

            while True:
                construct_kind_cluster('learn', CONST.K8S_VERSION)
                deployed = self.deploy.deploy_with_retry(self.context, 'learn')
                if deployed:
                    break
            apiclient = kubernetes_client('learn')
            runner = Runner(self.context, 'learn', 'learn')
            runner.run_without_collect(seed_file)

            update_preload_images(self.context)
            process_crd(self.context, apiclient, 'learn', self.crd_name, helper_crd)
            with open(context_file, 'w') as context_fout:
                json.dump(self.context, context_fout, cls=ActoEncoder)

        # Add additional preload images from arguments
        if preload_images_ != None:
            self.context['preload_images'].update(preload_images_)

        # Apply custom fields
        self.input_model = InputModel(self.context['crd']['body'], num_workers, mount)
        self.input_model.initialize(self.seed)
        if custom_fields_src != None:
            module = importlib.import_module(custom_fields_src)
            for custom_field in module.custom_fields:
                self.input_model.apply_custom_field(custom_field)

        # Generate test cases
        self.test_plan = self.input_model.generate_test_plan()
        with open(os.path.join(self.workdir_path, 'test_plan.json'), 'w') as plan_file:
            json.dump(self.test_plan, plan_file, cls=ActoEncoder, indent=6)

    def run(self):
        threads = []
        for i in range(self.num_workers):
            runner = TrialRunner(self.context, self.input_model, self.deploy, self.workdir_path, i,
                                 self.dryrun)
            t = threading.Thread(target=runner.run, args=())
            t.start()
            threads.append(t)

        for t in threads:
            t.join()


def handle_excepthook(type, message, stack):
    '''Custom exception handler
    
    Print detailed stack information with local variables
    '''
    if issubclass(type, KeyboardInterrupt):
        sys.__excepthook__(type, message, stack)
        return

    stack_info = traceback.StackSummary.extract(traceback.walk_tb(stack),
                                                capture_locals=True).format()
    logging.critical(f'An exception occured: {type}: {message}.')
    for i in stack_info:
        logging.critical(i.encode().decode('unicode-escape'))
    return


def thread_excepthook(args, /):
    exc_type = args.exc_type
    exc_value = args.exc_value
    exc_traceback = args.exc_traceback
    thread = args.thread
    if issubclass(exc_type, KeyboardInterrupt):
        threading.__excepthook__(args)
        return

    stack_info = traceback.StackSummary.extract(traceback.walk_tb(exc_traceback),
                                                capture_locals=True).format()
    logging.critical(f'An exception occured: {exc_type}: {exc_value}.')
    for i in stack_info:
        logging.critical(i.encode().decode('unicode-escape'))
    return


if __name__ == '__main__':
    start_time = time.time()
    workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')

    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
    parser.add_argument('--seed', '-s', dest='seed', required=True, help="seed CR file")
    deploy_method = parser.add_mutually_exclusive_group(required=True)
    deploy_method.add_argument('--operator',
                               '-o',
                               dest='operator',
                               required=False,
                               help="yaml file for deploying the\
                                operator with kubectl")
    deploy_method.add_argument('--helm',
                               dest='operator_chart',
                               required=False,
                               help='Path of operator helm chart')
    deploy_method.add_argument('--kustomize',
                               dest='kustomize',
                               required=False,
                               help='Path of folder with kustomize')
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
    parser.add_argument('--crd-name',
                        dest='crd_name',
                        help='Name of CRD to use, required if there are multiple CRDs')
    # Temporary solution before integrating controller-gen
    parser.add_argument('--helper-crd',
                        dest='helper_crd',
                        help='generated CRD file that helps with the input generation')
    parser.add_argument('--custom-fields',
                        dest='custom_fields',
                        help='Python source file containing a list of custom fields')
    parser.add_argument('--context', dest='context', help='Cached context data')
    parser.add_argument('--num-workers',
                        dest='num_workers',
                        type=int,
                        default=1,
                        help='Number of concurrent workers to run Acto with')
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
        '%(asctime)s %(threadName)-11s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s'
    )
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    # Register custom exception hook
    sys.excepthook = handle_excepthook
    threading.excepthook = thread_excepthook

    # We don't need this now, but it would be nice to support this in the future
    # candidate_dict = construct_candidate_from_yaml(args.candidates)
    # logging.debug(candidate_dict)

    logging.info('Acto started with [%s]' % sys.argv)

    # Preload frequently used images to amid ImagePullBackOff
    if args.preload_images:
        logging.info('%s will be preloaded into Kind cluster', args.preload_images)

    # register timeout to automatically stop after # hours
    if args.duration != None:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(args.duration) * 60 * 60)
    if args.operator_chart:
        deploy = Deploy(DeployMethod.HELM, args.operator_chart, args.init).new()
    elif args.operator:
        deploy = Deploy(DeployMethod.YAML, args.operator, args.init).new()
    elif args.kustomize:
        deploy = Deploy(DeployMethod.KUSTOMIZE, args.kustomize, args.init).new()
    else:
        raise UnknownDeployMethodError()

    if args.context == None:
        context_cache = os.path.join(os.path.dirname(args.seed), 'context.json')
    else:
        context_cache = args.context

    acto = Acto(args.seed, deploy, workdir_path, args.crd_name, args.preload_images,
                args.custom_fields, args.helper_crd, context_cache, args.num_workers, args.dryrun)
    acto.run()