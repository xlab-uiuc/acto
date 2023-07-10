import importlib
import json
import os
import subprocess
import tempfile
import time
from typing import List, Tuple

import yaml
from ray.util import ActorPool

from acto.checker.checker_set import CheckerSet
from acto.common import print_event
from acto.config import actoConfig
from acto.constant import CONST
from acto.deploy import DeployMethod, YamDeploy
from acto.input import InputModel, TestCase, DeterministicInputModel
from acto.input.input import OverSpecifiedField
from acto.input.known_schemas import find_all_matched_schemas_type, K8sField
from acto.input.valuegenerator import ArrayGenerator
from acto.kubernetes_engine.kind import Kind
from acto.lib.fp import drop_first_parameter
from acto.runner.ray_runner import Runner
from acto.runner.snapshot_collector import apply_system_input_and_wait, CollectorContext, with_context, snapshot_collector
from acto.runner.trial import Trial, TrialInputIterator
from acto.schema import ObjectSchema
from acto.serialization import ContextEncoder
from acto.utils import OperatorConfig, get_thread_logger, AnalysisConfig, update_preload_images, process_crd
from ssa.analysis import analyze


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
                 is_reproduce: bool,
                 reproduce_dir: str = None,
                 delta_from: str = None,
                 mount: list = None,
                 focus_fields: list = None,
                 checkers: CheckerSet = None,
                 num_of_mutations=10
                 ) -> None:
        logger = get_thread_logger(with_prefix=False)
        self.images_archive = os.path.join(workdir_path, 'images.tar')

        try:
            with open(operator_config.seed_custom_resource, 'r') as cr_file:
                seed = yaml.load(cr_file, Loader=yaml.FullLoader)
        except:
            logger.error('Failed to read seed yaml, aborting')
            quit()

        if operator_config.deploy.method != DeployMethod.YAML:
            logger.error('Only YAML deploy method is supported, aborting')
            quit()

        self.deploy = YamDeploy(operator_config.deploy.file, operator_config.deploy.init)

        if cluster_runtime != "KIND":
            logger.error('Only KIND cluster runtime is supported, aborting')
            quit()

        self.runners = ActorPool([Runner.remote(Kind, CONST.K8S_VERSION, operator_config.num_nodes) for _ in range(num_workers)])

        self.__learn_context(context_file=context_file,
                             crd_name=operator_config.crd_name,
                             helper_crd=helper_crd,
                             analysis_config=operator_config.analysis)

        if operator_config.analysis != None:
            used_fields = self.context['analysis_result']['used_fields']
        else:
            used_fields = None
        self.input_model: InputModel = DeterministicInputModel(self.context['crd']['body'],
                                                               used_fields,
                                                               operator_config.example_dir, num_workers,
                                                               num_cases, None, mount)
        self.input_model.initialize(seed)

        applied_custom_k8s_fields = False

        if operator_config.k8s_fields is not None:
            module = importlib.import_module(operator_config.k8s_fields)
            if hasattr(module, 'BLACKBOX') and actoConfig.mode == 'blackbox':
                for k8s_field in module.BLACKBOX:
                    self.input_model.apply_k8s_schema(k8s_field)
            elif hasattr(module, 'WHITEBOX') and actoConfig.mode == 'whitebox':
                applied_custom_k8s_fields = True
                for k8s_field in module.WHITEBOX:
                    self.input_model.apply_k8s_schema(k8s_field)
        if not applied_custom_k8s_fields:
            # default to use the known_schema module to automatically find the mapping
            # from CRD to K8s schema
            tuples = find_all_matched_schemas_type(self.input_model.root_schema)
            for tuple in tuples:
                logger.debug(f'Found matched schema: {tuple[0].path} -> {tuple[1]}')
                k8s_schema = K8sField(tuple[0].path, tuple[1])
                self.input_model.apply_k8s_schema(k8s_schema)

        if operator_config.custom_fields is not None:
            if actoConfig.mode == 'blackbox':
                pruned_list = []
                module = importlib.import_module(operator_config.custom_fields)
                for custom_field in module.custom_fields:
                    pruned_list.append(custom_field.path)
                    self.input_model.apply_custom_field(custom_field)
            else:
                pruned_list = []
                module = importlib.import_module(operator_config.custom_fields)
                for custom_field in module.custom_fields:
                    pruned_list.append(custom_field.path)
                    self.input_model.apply_custom_field(custom_field)
        else:
            pruned_list = []
            tuples = find_all_matched_schemas_type(self.input_model.root_schema)
            for tuple in tuples:
                custom_field = OverSpecifiedField(tuple[0].path, array=isinstance(tuple[1], ArrayGenerator))
                self.input_model.apply_custom_field(custom_field)

        # Generate test cases
        testplan_path = None
        if delta_from is not None:
            testplan_path = os.path.join(delta_from, 'test_plan.json')
        self.test_plan = self.input_model.generate_test_plan(testplan_path,
                                                             focus_fields=focus_fields)

        if checkers is None:
            self.checkers = CheckerSet(self.context, self.input_model)
        self.checkers = checkers
        self.num_of_mutations = num_of_mutations

    def __learn_context(self, context_file, crd_name, helper_crd, analysis_config):
        logger = get_thread_logger(with_prefix=False)
        context_file_up_to_date = os.path.exists(context_file)

        if context_file_up_to_date:
            logger.info('Loading context from file')
            with open(context_file, 'r') as context_fin:
                self.context = json.load(context_fin)
                self.context['preload_images'] = set(self.context['preload_images'])
            return

        # Run learning run to collect some information from runtime
        context = {'namespace': '', 'crd': None, 'preload_images': set()}
        learn_task_context = CollectorContext()

        class LearnCompleteException(Exception):
            context: dict

        def collect_learn_context(namespace_discovered: str, runner: Runner, trial: Trial, seed_input: dict):
            logger.info('Starting learning run to collect information')
            learn_task_context.namespace = namespace_discovered
            apply_system_input_and_wait(learn_task_context, runner, seed_input)

            update_preload_images(context, runner.cluster.get_node_list(runner.kubectl_client.context_name))
            process_crd(context, runner.kubectl_client.api_client, runner.kubectl_client, crd_name, helper_crd)

            raise LearnCompleteException(context)

        task = self.deploy.chain_with(collect_learn_context)
        # TODO, add protocols to Trial to suppress type error
        runner_trial = Trial((), None)
        self.runners.submit(lambda runner, trial: runner.run.remote(trial, task), runner_trial)
        runner_trial = self.runners.get_next()
        assert isinstance(runner_trial.error, LearnCompleteException)

        self.context = runner_trial.error.context
        self.context['analysis_result'] = do_static_analysis(analysis_config)

        with open(context_file, 'w') as context_fout:
            json.dump(self.context, context_fout, cls=ContextEncoder, indent=4, sort_keys=True)

    def run(self, modes=None):
        if modes is None:
            modes = ['normal', 'overspecified', 'copiedover']

        logger = get_thread_logger(with_prefix=True)

        # Build an archive to be preloaded
        if len(self.context['preload_images']) > 0:
            logger.info('Creating preload images archive')
            print_event('Preparing required images...')
            # first make sure images are present locally
            for image in self.context['preload_images']:
                subprocess.run(['docker', 'pull', image], stdout=subprocess.DEVNULL)
            subprocess.run(['docker', 'image', 'save', '-o', self.images_archive] +
                           list(self.context['preload_images']), stdout=subprocess.DEVNULL)

        start_time = time.time()

        def run_test_plan(test_case_list: List[Tuple[List[str], TestCase]]):
            active_runner_count = 0
            while active_runner_count != 0 and len(test_case_list) != 0:
                def task(runner: Runner, test_cases: List[Tuple[List[str], TestCase]]) -> Trial:
                    collector = with_context(CollectorContext(
                        namespace=self.context['namespace'],
                        crd_meta_info=self.context['crd'],
                    ), snapshot_collector)

                    collector = self.deploy.chain_with(drop_first_parameter(collector))
                    assert isinstance(self.input_model.get_root_schema(), ObjectSchema)
                    iterator = TrialInputIterator(iter(test_cases), self.input_model.get_root_schema(), self.input_model.get_seed_input())

                    trial = Trial(iterator, self.checkers, num_mutation=self.num_of_mutations)
                    runner.run(trial, collector)
                    return trial

                while self.runners.has_free() and len(test_case_list) != 0:
                    test_cases, test_case_list = test_case_list[:self.num_of_mutations], test_case_list[self.num_of_mutations:]
                    self.runners.submit(task, test_cases)
                    active_runner_count += 1

                trial: Trial = self.runners.get_next_unordered()
                active_runner_count -= 1
                for test_case in trial.next_input.next_testcase:
                    test_case_list.append(test_case)

        if 'normal' in modes:
            run_test_plan(self.test_plan['normal_subgroups'])

        if 'overspecified' in modes:
            run_test_plan(self.test_plan['overspecified_subgroups'])

        if 'copiedover' in modes:
            run_test_plan(self.test_plan['copiedover_subgroups'])

        if InputModel.ADDITIONAL_SEMANTIC in modes:
            run_test_plan(self.test_plan['additional_semantic_subgroups'])

        logger.info('All tests finished')


def do_static_analysis(analysis: AnalysisConfig):
    with tempfile.TemporaryDirectory() as project_src:
        subprocess.run(['git', 'clone', analysis.github_link, project_src])
    subprocess.run(['git', '-C', project_src, 'checkout', analysis.commit])

    if analysis.entrypoint is not None:
        entrypoint_path = os.path.join(project_src, analysis.entrypoint)
    else:
        entrypoint_path = project_src
    return analyze(entrypoint_path, analysis.type, analysis.package)
