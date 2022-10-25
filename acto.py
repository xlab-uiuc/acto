import argparse
import os
import sys
import threading
from types import SimpleNamespace
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
import tempfile
import jsonpatch

from common import *
from exception import UnknownDeployMethodError
from k8s_helper import delete_operator_pod
from preprocess import add_acto_label, process_crd, update_preload_images
from input import InputModel
from deploy import Deploy, DeployMethod
from k8s_cluster import base, k3d, kind
from constant import CONST
from runner import Runner
from checker import Checker
from schema import BaseSchema, ObjectSchema, ArraySchema
from snapshot import EmptySnapshot
from ssa.analysis import analyze
from thread_logger import set_thread_logger_prefix, get_thread_logger
from value_with_schema import ValueWithSchema, attach_schema_to_value

CONST = CONST()
random.seed(0)

notify_crash_ = False


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


def apply_testcase(value_with_schema: ValueWithSchema,
                   path: list,
                   testcase: TestCase,
                   setup: bool = False) -> jsonpatch.JsonPatch:
    logger = get_thread_logger(with_prefix=True)

    prev = value_with_schema.raw_value()
    field_curr_value = value_with_schema.get_value_by_path(list(path))
    if setup:
        value_with_schema.create_path(list(path))
        value_with_schema.set_value_by_path(testcase.setup(field_curr_value), list(path))
        curr = value_with_schema.raw_value()
    else:
        if testcase.test_precondition(field_curr_value):
            value_with_schema.create_path(list(path))
            value_with_schema.set_value_by_path(testcase.mutator(field_curr_value), list(path))
            curr = value_with_schema.raw_value()

    patch = jsonpatch.make_patch(prev, curr)
    logger.info('JSON patch: %s' % patch)
    return patch


def timeout_handler(sig, frame):
    raise TimeoutError


class TrialRunner:

    def __init__(self, context: dict, input_model: InputModel, deploy: Deploy, workdir: str,
                 cluster: base.KubernetesCluster, worker_id: int, dryrun: bool) -> None:
        self.context = context
        self.workdir = workdir
        self.cluster = cluster
        self.images_archive = os.path.join(workdir, 'images.tar')
        self.worker_id = worker_id
        self.context_name = cluster.get_context_name(
            f"acto-cluster-{worker_id}")
        self.kubeconfig = os.path.join(os.path.expanduser('~'), '.kube', self.context_name)
        self.cluster_name = f"acto-cluster-{worker_id}"
        self.input_model = input_model
        self.deploy = deploy
        self.dryrun = dryrun

        self.snapshots = []
        self.discarded_testcases = {}  # List of test cases failed to run
        
    def run(self):
        logger = get_thread_logger(with_prefix=False)
        
        self.input_model.set_worker_id(self.worker_id)
        curr_trial = 0
        apiclient = None

        while True:
            trial_start_time = time.time()
            self.cluster.configure_cluster(4, CONST.K8S_VERSION)
            self.cluster.restart_cluster(self.cluster_name, self.kubeconfig, CONST.K8S_VERSION)
            apiclient = kubernetes_client(self.kubeconfig, self.context_name)
            self.cluster.load_images(self.images_archive, self.cluster_name)
            deployed = self.deploy.deploy_with_retry(
                self.context, self.kubeconfig, self.context_name)
            if not deployed:
                logger.info('Not deployed. Try again!')
                continue

            add_acto_label(apiclient, self.context)

            trial_dir = os.path.join(self.workdir, 'trial-%02d-%04d' % (self.worker_id, curr_trial))
            os.makedirs(trial_dir, exist_ok=True)

            trial_err, num_tests = self.run_trial(trial_dir=trial_dir, curr_trial=curr_trial)
            self.snapshots = []

            trial_elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - trial_start_time))
            logger.info('Trial %d finished, completed in %s' % (curr_trial, trial_elapsed))
            logger.info('---------------------------------------\n')

            delete_operator_pod(apiclient, self.context['namespace'])
            save_result(trial_dir, trial_err, num_tests, trial_elapsed)
            curr_trial = curr_trial + 1

            if self.input_model.is_empty():
                logger.info('Test finished')
                break

        logger.info('Failed test cases: %s' %
                     json.dumps(self.discarded_testcases, cls=ActoEncoder, indent=4))

    def run_trial(self, trial_dir: str, curr_trial: int, num_mutation: int = 10) -> Tuple[ErrorResult, int]:
        '''Run a trial starting with the initial input, mutate with the candidate_dict, 
        and mutate for num_mutation times

        Args:
            initial_input: the initial input without mutation
            candidate_dict: guides the mutation
            trial_num: how many trials have been run
            num_mutation: how many mutations to run at each trial
        '''

        runner = Runner(self.context, trial_dir, self.kubeconfig, self.context_name)
        checker = Checker(self.context, trial_dir, self.input_model)

        curr_input = self.input_model.get_seed_input()
        self.snapshots.append(EmptySnapshot(curr_input))

        generation = 0
        while generation < num_mutation:  # every iteration gets a new list of next tests
            # update the thread logger
            set_thread_logger_prefix(f'trial: {curr_trial}, gen: {generation}')
            logger = get_thread_logger(with_prefix=True)

            curr_input_with_schema = attach_schema_to_value(self.snapshots[-1].input,
                                                            self.input_model.root_schema)

            ready_testcases = []
            if generation > 0:
                if self.input_model.is_empty():
                    break
                next_tests = self.input_model.next_test()

                for (field_node, testcase) in next_tests:  # iterate on list of next tests
                    field_curr_value = curr_input_with_schema.get_value_by_path(
                        list(field_node.get_path()))

                    if testcase.test_precondition(field_curr_value):
                        # precondition of this testcase satisfies
                        logger.info('Precondition of %s satisfies', field_node.get_path())
                        ready_testcases.append((field_node, testcase))
                    else:
                        # precondition fails, first run setup
                        logger.info('Precondition of %s fails, try setup first',
                                     field_node.get_path())
                        apply_testcase(curr_input_with_schema,
                                       field_node.get_path(),
                                       testcase,
                                       setup=True)

                        if not testcase.test_precondition(
                                curr_input_with_schema.get_value_by_path(list(
                                    field_node.get_path()))):
                            # just in case the setup does not work correctly, drop this testcase
                            logger.error('Setup does not work correctly')
                            field_node.discard_testcase(self.discarded_testcases)
                            continue

                        result = TrialRunner.run_and_check(runner, checker,
                                                           curr_input_with_schema.raw_value(),
                                                           self.snapshots, generation, self.dryrun)
                        generation += 1

                        if isinstance(result, InvalidInputResult):
                            logger.info('Setup produced invalid input')
                            self.snapshots.pop()
                            field_node.discard_testcase(self.discarded_testcases)
                            curr_input_with_schema = self.revert(runner, checker, generation)
                            generation += 1
                        elif isinstance(result, UnchangedInputResult):
                            field_node.discard_testcase(self.discarded_testcases)
                        elif isinstance(result, ErrorResult):
                            field_node.discard_testcase(self.discarded_testcases)
                            # before return, run the recovery test case
                            recovery_result = self.run_recovery(runner, checker, generation)
                            generation += 1

                            if isinstance(recovery_result, RecoveryResult):
                                logger.debug('Recovery failed')
                                return CompoundErrorResult(result, recovery_result), generation
                            else:
                                return result, generation
                        elif isinstance(result, PassResult):
                            ready_testcases.append((field_node, testcase))
                        else:
                            logger.error('Unknown return value, abort')
                            quit()

                if len(ready_testcases) == 0:
                    logger.info('All setups failed')
                    continue
                logger.info('Running bundled testcases')

            t = self.run_testcases(curr_input_with_schema, ready_testcases, runner, checker,
                                   generation)
            logger.debug(t)
            result, generation = t
            if isinstance(result, ErrorResult):
                # before return, run the recovery test case
                recovery_result = self.run_recovery(runner, checker, generation)
                generation += 1

                if isinstance(recovery_result, RecoveryResult):
                    logger.debug('Recovery failed')
                    return CompoundErrorResult(result, recovery_result), generation
                else:
                    return result, generation

            if self.input_model.is_empty():
                break

        return None, generation

    def run_testcases(self, curr_input_with_schema, testcases, runner, checker,
                      generation) -> Tuple[RunResult, int]:
        logger = get_thread_logger(with_prefix=True)
        
        testcase_patches = []
        for field_node, testcase in testcases:
            patch = apply_testcase(curr_input_with_schema, field_node.get_path(), testcase)
            # field_node.get_testcases().pop()  # finish testcase
            testcase_patches.append((field_node, testcase, patch))

        result = TrialRunner.run_and_check(runner, checker, curr_input_with_schema.raw_value(),
                                           self.snapshots, generation, self.dryrun)
        generation += 1
        if isinstance(result, InvalidInputResult):
            # If the result indicates our input is invalid, we need to first run revert to
            # go back to previous system state, then construct a new input without the
            # responsible testcase and re-apply

            # 1. revert
            logger.debug('Invalid input, revert')
            self.snapshots.pop()
            curr_input_with_schema = self.revert(runner, checker, generation)
            generation += 1

            # 2. Construct a new input and re-apply
            if len(testcase_patches) == 1:
                # if only one testcase, then no need to isolate
                testcase_patches[0][0].get_testcases().pop()  # finish testcase
                logger.debug('Only one patch, no need to isolate')
                return result, generation
            else:
                responsible_field = result.responsible_field
                if responsible_field == None:
                    # Unable to pinpoint the exact responsible testcase, try one by one
                    logger.debug('Unable to pinpoint the exact responsible field, try one by one')
                    for field_node, testcase, patch in testcase_patches:
                        result, generation = self.run_testcases(curr_input_with_schema,
                                                                [(field_node, testcase)], runner,
                                                                checker, generation)
                        if isinstance(result, ErrorResult):
                            return result, generation
                    return result, generation
                else:
                    jsonpatch_path = ''.join('/' + str(item) for item in responsible_field)
                    logger.debug('Responsible patch path: %s', jsonpatch_path)
                    # isolate the responsible invalid testcase and re-apply
                    ready_testcases = []
                    for field_node, testcase, patch in testcase_patches:
                        responsible = False
                        for op in patch:
                            if op['path'] == jsonpatch_path:
                                logger.info('Determine the responsible field to be %s' %
                                             jsonpatch_path)
                                responsible = True
                                field_node.get_testcases().pop()  # finish testcase
                                break
                        if not responsible:
                            ready_testcases.append((field_node, testcase))
                    if len(ready_testcases) == 0:
                        return result, generation

                    if len(ready_testcases) == len(testcase_patches):
                        logger.error('Fail to determine the responsible patch, try one by one')
                        for field_node, testcase, patch in testcase_patches:
                            result, generation = self.run_testcases(curr_input_with_schema,
                                                                    [(field_node, testcase)], runner,
                                                                    checker, generation)
                            if isinstance(result, ErrorResult):
                                return result, generation
                        return result, generation
                    else:
                        logger.debug('Rerunning the remaining ready testcases')
                        return self.run_testcases(curr_input_with_schema, ready_testcases, runner,
                                                checker, generation)
        else:
            for patch in testcase_patches:
                patch[0].get_testcases().pop()  # finish testcase
            if isinstance(result, UnchangedInputResult):
                pass
            elif isinstance(result, ErrorResult):
                # TODO: Delta debugging
                pass
            elif isinstance(result, PassResult):
                pass
            else:
                logger.error('Unknown return value, abort')
                quit()
            return result, generation

    def run_and_check(runner: Runner, checker: Checker, input: dict, snapshots: list,
                      generation: int, dryrun: bool) -> RunResult:
        logger = get_thread_logger(with_prefix=True)
        logger.debug('Run and check')
        while True:
            if not dryrun:
                snapshot = runner.run(input, generation)
                result = checker.check(snapshot, snapshots[-1], generation)
                snapshots.append(snapshot)
            else:
                result = PassResult()

            if isinstance(result, ConnectionRefusedResult):
                # Connection refused due to webhook not ready, let's wait for a bit
                logger.info('Connection failed. Retry the test after 20 seconds')
                time.sleep(20)
            else:
                break
        return result

    def run_recovery(self, runner: Runner, checker: Checker, generation: int) -> RunResult:
        '''Runs the recovery test case after an error is reported'''
        logger = get_thread_logger(with_prefix=True)
        RECOVERY_SNAPSHOT = -2  # the immediate snapshot before the error

        logger.debug('Running recovery')
        recovery_input = self.snapshots[RECOVERY_SNAPSHOT].input
        snapshot = runner.run(recovery_input, generation=-1)
        result = checker.check_state_equality(snapshot, self.snapshots[RECOVERY_SNAPSHOT])

        return result

    def revert(self, runner, checker, generation) -> ValueWithSchema:
        curr_input_with_schema = attach_schema_to_value(self.snapshots[-1].input,
                                                        self.input_model.root_schema)

        result = TrialRunner.run_and_check(runner, checker, curr_input_with_schema.raw_value(),
                                           self.snapshots, generation, self.dryrun)
        return curr_input_with_schema


class Acto:

    def __init__(self,
                 workdir_path: str,
                 operator_config: OperatorConfig,
                 cluster_runtime: str,
                 enable_analysis: bool,
                 preload_images_: list,
                 context_file: str,
                 helper_crd: str,
                 num_workers: int,
                 num_cases: int,
                 dryrun: bool,
                 analysis_only: bool,
                 mount: list = None) -> None:
        logger = get_thread_logger(with_prefix=False)

        try:
            with open(operator_config.seed_custom_resource, 'r') as cr_file:
                self.seed = yaml.load(cr_file, Loader=yaml.FullLoader)
        except:
            logger.error('Failed to read seed yaml, aborting')
            quit()

        if operator_config.deploy.method == 'HELM':
            deploy = Deploy(DeployMethod.HELM, operator_config.deploy.file,
                            operator_config.deploy.init).new()
        elif operator_config.deploy.method == 'YAML':
            deploy = Deploy(DeployMethod.YAML, operator_config.deploy.file,
                            operator_config.deploy.init).new()
        elif operator_config.deploy.method == 'KUSTOMIZE':
            deploy = Deploy(DeployMethod.KUSTOMIZE, operator_config.deploy.file,
                            operator_config.deploy.init).new()
        else:
            raise UnknownDeployMethodError()

        if cluster_runtime == "KIND":
            cluster = kind.Kind()
        elif cluster_runtime == "K3D":
            cluster = k3d.K3D()
        else:
            logger.warning(
                f"Cluster Runtime {cluster_runtime} is not supported, defaulted to use kind")
            cluster = kind.Kind()

        self.cluster = cluster
        self.deploy = deploy
        self.operator_config = operator_config
        self.crd_name = operator_config.crd_name
        self.workdir_path = workdir_path
        self.images_archive = os.path.join(workdir_path, 'images.tar')
        self.num_workers = num_workers
        self.dryrun = dryrun
        self.snapshots = []

        # generate configuration files for the cluster runtime
        self.cluster.configure_cluster(4, CONST.K8S_VERSION)

        self.__learn(context_file=context_file, helper_crd=helper_crd, analysis_only=analysis_only)

        self.context['enable_analysis'] = enable_analysis

        # Add additional preload images from arguments
        if preload_images_ != None:
            self.context['preload_images'].update(preload_images_)

        # Apply custom fields
        self.input_model = InputModel(self.context['crd']['body'], operator_config.example_dir,
                                      num_workers, num_cases, mount)
        self.input_model.initialize(self.seed)
        if operator_config.custom_fields != None:
            pruned_list = []
            module = importlib.import_module(operator_config.custom_fields)
            for custom_field in module.custom_fields:
                pruned_list.append(custom_field.path)
                self.input_model.apply_custom_field(custom_field)

            logger.info("Applied custom fields: %s", json.dumps(pruned_list))

        # Generate test cases
        self.test_plan = self.input_model.generate_test_plan()
        with open(os.path.join(self.workdir_path, 'test_plan.json'), 'w') as plan_file:
            json.dump(self.test_plan, plan_file, cls=ActoEncoder, indent=4)

    def __learn(self, context_file, helper_crd, analysis_only=False):
        logger = get_thread_logger(with_prefix=False)

        if os.path.exists(context_file):
            logger.info('Loading context from file')
            with open(context_file, 'r') as context_fin:
                self.context = json.load(context_fin)
                self.context['preload_images'] = set(self.context['preload_images'])

            if analysis_only and self.operator_config.analysis != None:
                logger.info('Only run learning analysis')
                with tempfile.TemporaryDirectory() as project_src:
                    subprocess.run(
                        ['git', 'clone', self.operator_config.analysis.github_link, project_src])
                    subprocess.run([
                        'git', '-C', project_src, 'checkout', self.operator_config.analysis.commit
                    ])

                    if self.operator_config.analysis.entrypoint != None:
                        entrypoint_path = os.path.join(project_src,
                                                    self.operator_config.analysis.entrypoint)
                    else:
                        entrypoint_path = project_src
                    self.context['analysis_result'] = analyze(entrypoint_path,
                                                            self.operator_config.analysis.type,
                                                            self.operator_config.analysis.package)
                with open(context_file, 'w') as context_fout:
                    json.dump(self.context, context_fout, cls=ContextEncoder, indent=6)
        else:
            # Run learning run to collect some information from runtime
            logger.info('Starting learning run to collect information')
            self.context = {'namespace': '', 'crd': None, 'preload_images': set()}
            learn_context_name = self.cluster.get_context_name('learn')
            learn_kubeconfig = os.path.join(os.path.expanduser('~'), '.kube', self.learn_context_name)

            while True:
                self.cluster.restart_cluster('learn', CONST.K8S_VERSION)
                deployed = self.deploy.deploy_with_retry(
                    self.context, learn_kubeconfig, learn_context_name)
                if deployed:
                    break
            apiclient = kubernetes_client(learn_kubeconfig, learn_context_name)
            runner = Runner(self.context, 'learn', learn_kubeconfig,
                            learn_context_name)
            runner.run_without_collect(
                self.operator_config.seed_custom_resource)

            update_preload_images(
                self.context, self.cluster.get_node_list('learn'))
            process_crd(self.context, apiclient, 'learn', learn_kubeconfig, learn_context_name,
                        self.crd_name, helper_crd)
            self.cluster.delete_cluster('learn')

            if self.operator_config.analysis != None:
                with tempfile.TemporaryDirectory() as project_src:
                    subprocess.run(
                        ['git', 'clone', self.operator_config.analysis.github_link, project_src])
                    subprocess.run([
                        'git', '-C', project_src, 'checkout', self.operator_config.analysis.commit
                    ])

                    if self.operator_config.analysis.entrypoint != None:
                        entrypoint_path = os.path.join(project_src,
                                                       self.operator_config.analysis.entrypoint)
                    else:
                        entrypoint_path = project_src
                    self.context['analysis_result'] = analyze(entrypoint_path,
                                                              self.operator_config.analysis.type,
                                                              self.operator_config.analysis.package)
            with open(context_file, 'w') as context_fout:
                json.dump(self.context, context_fout, cls=ContextEncoder, indent=6, sort_keys=True)

    def run(self):
        logger = get_thread_logger(with_prefix=False)

        # Build an archive to be preloaded
        if len(self.context['preload_images']) > 0:
            logger.info('Creating preload images archive')
            # first make sure images are present locally
            for image in self.context['preload_images']:
                subprocess.run(['docker', 'pull', image])
            subprocess.run(['docker', 'image', 'save', '-o', self.images_archive] +
                           list(self.context['preload_images']))

        threads = []
        for i in range(self.num_workers):
            runner = TrialRunner(self.context, self.input_model, self.deploy, self.workdir_path, self.cluster,
                                 i, self.dryrun)
            t = threading.Thread(target=runner.run, args=())
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
        logger.info('All tests finished')

def handle_excepthook(type, message, stack):
    '''Custom exception handler

    Print detailed stack information with local variables
    '''
    logger = get_thread_logger(with_prefix=True)

    if issubclass(type, KeyboardInterrupt):
        sys.__excepthook__(type, message, stack)
        return

    global notify_crash_
    if notify_crash_:
        notify_crash(f'An exception occured: {type}: {message}.')

    stack_info = traceback.StackSummary.extract(traceback.walk_tb(stack),
                                                capture_locals=True).format()
    logger.critical(f'An exception occured: {type}: {message}.')
    for i in stack_info:
        logger.critical(i.encode().decode('unicode-escape'))
    return


def thread_excepthook(args):
    logger = get_thread_logger(with_prefix=True)

    exc_type = args.exc_type
    exc_value = args.exc_value
    exc_traceback = args.exc_traceback
    thread = args.thread
    if issubclass(exc_type, KeyboardInterrupt):
        threading.__excepthook__(args)
        return

    global notify_crash_
    if notify_crash_:
        notify_crash(f'An exception occured: {exc_type}: {exc_value}.')

    stack_info = traceback.StackSummary.extract(traceback.walk_tb(exc_traceback),
                                                capture_locals=True).format()
    logger.critical(f'An exception occured: {exc_type}: {exc_value}.')
    for i in stack_info:
        logger.critical(i.encode().decode('unicode-escape'))
    return


if __name__ == '__main__':
    start_time = time.time()
    workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')

    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
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

    # Register custom exception hook
    sys.excepthook = handle_excepthook
    threading.excepthook = thread_excepthook

    if args.notify_crash:
        notify_crash_ = True

    with open(args.config, 'r') as config_file:
        config = json.load(config_file, object_hook=lambda d: SimpleNamespace(**d))
    logger.info('Acto started with [%s]' % sys.argv)
    logger.info('Operator config: %s', config)

    # Preload frequently used images to amid ImagePullBackOff
    if args.preload_images:
        logger.info('%s will be preloaded into Kind cluster', args.preload_images)

    # register timeout to automatically stop after # hours
    if args.duration != None:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(args.duration) * 60 * 60)

    if args.context == None:
        context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')
    else:
        context_cache = args.context

    start_time = datetime.now()
    acto = Acto(workdir_path, config, args.cluster_runtime, args.enable_analysis, args.preload_images, context_cache,
                args.helper_crd, args.num_workers, args.num_cases, args.dryrun, args.learn_analysis_only)
    if not args.learn:
        acto.run()
    end_time = datetime.now()
    logger.info('Acto finished in %s', end_time - start_time)
