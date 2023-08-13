import asyncio
import importlib
import inspect
import json
import os
import dill as pickle
import subprocess
import tempfile
from typing import List, Tuple, Callable, Sequence

import yaml
from acto.checker.checker import Checker

from acto import ray_acto as ray
from acto.ray_acto.util import ActorPool
from acto.checker.checker_set import CheckerSet, default_checker_generators
from acto.config import actoConfig
from acto.constant import CONST
from acto.deploy import DeployMethod, YamlDeploy
from acto.snapshot import Snapshot
from acto.input import InputModel, TestCase, DeterministicInputModel
from acto.input.input import OverSpecifiedField
from acto.input.known_schemas import find_all_matched_schemas_type, K8sField
from acto.input.valuegenerator import ArrayGenerator
from acto.kubernetes_engine.kind import Kind
from acto.lib.fp import drop_first_parameter
from acto.runner.runner import Runner
from acto.runner.snapshot_collector import CollectorContext, with_context, snapshot_collector, wait_for_system_converge
from acto.runner.trial import Trial, TrialInputIterator, TrialInputIteratorLike
from acto.schema import ObjectSchema
from acto.serialization import ContextEncoder
from acto.lib.operator_config import OperatorConfig, AnalysisConfig
from acto.utils import get_thread_logger, update_preload_images, process_crd
from ssa.analysis import analyze


def task(runner: Runner, data: Tuple[Callable[[Runner, Trial, dict],Snapshot], CheckerSet, int, TrialInputIteratorLike]) -> Trial:
    collector, checkers, num_of_mutations, iterator = data
    trial = Trial(iterator, checkers, num_mutation=num_of_mutations)
    return runner.run.remote(trial, collector)

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
                 checker_generators: list = None,
                 num_of_mutations=9
                 ) -> None:
        logger = get_thread_logger(with_prefix=False)
        self.workdir_path = workdir_path
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

        self.deploy = YamlDeploy(operator_config.deploy.file, operator_config.deploy.init)

        if cluster_runtime != "KIND":
            logger.error('Only KIND cluster runtime is supported, aborting')
            quit()

        self.__learn_context(runner=lambda :Runner.remote(Kind, CONST.K8S_VERSION, operator_config.num_nodes),
                             context_file=context_file,
                             crd_name=operator_config.crd_name,
                             helper_crd=helper_crd,
                             analysis_config=operator_config.analysis,
                             seed_file_path=operator_config.seed_custom_resource)

        if num_workers == 0:
            self.runners = None
        else:
            self.runners = ActorPool([Runner.remote(Kind, CONST.K8S_VERSION, operator_config.num_nodes, self.context['preload_images']) for _ in range(num_workers)])

        if operator_config.analysis is not None:
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

        if checker_generators is None:
            checker_generators = default_checker_generators
        for oracle_modules in operator_config.custom_oracles:
            module = importlib.import_module(oracle_modules)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Checker) and not inspect.isabstract(obj):
                    checker_generators.append(obj)

        self.checkers = CheckerSet(self.context, self.input_model, checker_generators)
        self.num_of_mutations = num_of_mutations
        self.trial_id = 0
        self.collect_coverage = operator_config.collect_coverage

    def __learn_context(self, runner: Callable[[],Runner], context_file, crd_name, helper_crd, analysis_config, seed_file_path):
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

            def __init__(self, ctx: dict):
                self.context = ctx

        def collect_learn_context(namespace_discovered: str, runner: Runner, trial: Trial, seed_input: dict):
            logger.info('Starting learning run to collect information')
            context['namespace'] = namespace_discovered
            runner.kubectl_client.apply(seed_input, namespace=namespace_discovered)

            learn_task_context.set_collector_if_none(runner.kubectl_client)
            asyncio.run(wait_for_system_converge(learn_task_context.kubectl_collector, learn_task_context.timeout))

            update_preload_images(context, runner.cluster.get_node_list(runner.cluster_name))
            process_crd(context, runner.kubectl_client.api_client, runner.kubectl_client, crd_name, helper_crd)

            raise LearnCompleteException(context)

        task = self.deploy.chain_with(collect_learn_context)
        # TODO, add protocols to Trial to suppress type error
        learn_runner = runner()
        runner_trial = Trial(TrialInputIterator(iter(()), None, yaml.safe_load(open(seed_file_path))), None)
        runner_trial = learn_runner.run.remote(runner_trial, task)
        runner_trial = ray.get(runner_trial)
        assert isinstance(runner_trial.error, LearnCompleteException)

        self.context = runner_trial.error.context
        if analysis_config:
            self.context['analysis_result'] = do_static_analysis(analysis_config)

        with open(context_file, 'w') as context_fout:
            json.dump(self.context, context_fout, cls=ContextEncoder, indent=4, sort_keys=True)

    def run_trials(self, iterators: Sequence[TrialInputIteratorLike], _collector: Callable[[Runner, Trial, dict], Snapshot] = None):
        if _collector is None:
            collector = with_context(CollectorContext(
                namespace=self.context['namespace'],
                crd_meta_info=self.context['crd'],
                collect_coverage=self.collect_coverage,
            ), snapshot_collector)
        else:
            collector = _collector
        # Inject the deploy step into the collector, to deploy the operator before running the test
        collector = self.deploy.chain_with(drop_first_parameter(collector))
        assert isinstance(self.input_model.get_root_schema(), ObjectSchema)
        for it in iterators:
            self.runners.submit(task, (collector, self.checkers, self.num_of_mutations, it))

        while self.runners.has_next():
            # As long as we have remaining test cases
            trial: Trial = self.runners.get_next_unordered()
            trial_save_dir = os.path.join(self.workdir_path, f'trial-{self.trial_id:05}')
            os.makedirs(trial_save_dir, exist_ok=True)
            # TODO: improve saving snapshots
            for (_, exception_or_snapshot_plus_oracle_result) in trial.history_iterator():
                if not isinstance(exception_or_snapshot_plus_oracle_result, Exception):
                    (snapshot, _) = exception_or_snapshot_plus_oracle_result
                    snapshot.save(trial_save_dir)
            pickle.dump(trial, open(os.path.join(trial_save_dir, 'trial.pkl'), 'wb'))
            self.trial_id += 1

    def run(self, modes=None):
        if modes is None:
            modes = ['normal', 'overspecified', 'copiedover']

        logger = get_thread_logger(with_prefix=True)

        def run_test_plan(test_case_list: List[Tuple[List[str], TestCase]]):
            iterators = []

            while len(test_case_list) != 0:
                test_cases, test_case_list = test_case_list[:self.num_of_mutations], test_case_list[self.num_of_mutations:]
                iterators.append(TrialInputIterator(iter(test_cases), self.input_model.get_root_schema(), self.input_model.get_seed_input()))

            self.run_trials(iterators)

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
