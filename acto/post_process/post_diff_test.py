import glob
import hashlib
import json
import logging
import os
import dill as pickle
import re
import sys
import threading
import time
from dataclasses import asdict
from functools import partial
from typing import Dict, List, Tuple, Generator, Iterator, Type, Callable, Iterable

import pandas as pd
from deepdiff.helper import CannotCompare
from deepdiff.model import DiffLevel
from deepdiff.operator import BaseOperator
from pandas import DataFrame

from acto.monkey_patch import monkey_patch

from acto.checker.checker import OracleResult, OracleControlFlow
from acto.checker.impl import recovery
from acto.checker.impl.recovery import RecoveryResult

from acto.constant import CONST
from acto.deploy import Deploy
from acto.input import TestCase
from acto.kubernetes_engine.kind import Kind
from acto.ray_acto import ray
from acto.runner.trial import Trial, unpack_history_iterator_or_raise
from acto.serialization import ActoEncoder
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger, handle_excepthook, thread_excepthook
from acto.lib.operator_config import OperatorConfig
from acto.lib.fp import drop_first_parameter, unreachable
from acto.ray_acto.util import ActorPool
from acto.runner.runner import Runner, Engine
from acto.runner.snapshot_collector import CollectorContext, with_context, snapshot_collector

from .post_process import PostProcessor

__test__ = False


def digest_input(system_input: dict):
    return hashlib.md5(json.dumps(system_input, sort_keys=True).encode("utf-8")).hexdigest()


def postprocess_deepdiff(diff):
    # ignore PVC add/removal, because PVC can be intentially left behind
    logger = get_thread_logger(with_prefix=False)
    if 'dictionary_item_removed' in diff:
        new_removed_items = []
        for removed_item in diff['dictionary_item_removed']:
            if removed_item.path(output_format='list')[0] == 'pvc':
                logger.debug(f"ignoring removed pvc {removed_item}")
            else:
                new_removed_items.append(removed_item)
        if len(new_removed_items) == 0:
            del diff['dictionary_item_removed']
        else:
            diff['dictionary_item_removed'] = new_removed_items

    if 'dictionary_item_added' in diff:
        new_removed_items = []
        for removed_item in diff['dictionary_item_added']:
            if removed_item.path(output_format='list')[0] == 'pvc':
                logger.debug(f"ignoring added pvc {removed_item}")
            else:
                new_removed_items.append(removed_item)
        if len(new_removed_items) == 0:
            del diff['dictionary_item_added']
        else:
            diff['dictionary_item_added'] = new_removed_items


def compare_func(x, y, level: DiffLevel = None):
    try:
        if 'name' not in x or 'name' not in y:
            return x['key'] == y['key'] and x['operator'] == y['operator']
        x_name = x['name']
        y_name = y['name']
        if len(x_name) < 5 or len(y_name) < 5:
            return x_name == y_name
        else:
            return x_name[:5] == y_name[:5]
    except:
        raise CannotCompare() from None


class NameOperator(BaseOperator):
    def __init__(self, *args):
        super().__init__(*args)
        self.regex = re.compile(r"^.+-([A-Za-z0-9]{5})$")

    def give_up_diffing(self, level, diff_instance):
        x_name = level.t1
        y_name = level.t2
        if x_name is None or y_name is None:
            return False
        if self.regex.search(x_name) and self.regex.search(y_name):
            return x_name[:5] == y_name[:5]
        return False


class TypeChangeOperator(BaseOperator):

    def give_up_diffing(self, level, diff_instance):
        if level.t1 is None:
            if isinstance(level.t2, dict):
                level.t1 = {}
            elif isinstance(level.t2, list):
                level.t1 = []
        elif level.t2 is None:
            if isinstance(level.t1, dict):
                logging.info('t2 is None, t1 is dict')
                level.t2 = {}
            elif isinstance(level.t1, list):
                level.t2 = []
        return False


compare_system_equality = partial(recovery.compare_system_equality, diff_operators=[
    NameOperator(r".*\['name'\]$"),
    TypeChangeOperator(r".*\['annotations'\]$")
], iterable_compare_func=compare_func)


def apply_postprocess_deepdiff(compare_system_equality_old):
    def compare_system_equality_new(*args, **kwargs):
        oracle_result = compare_system_equality_old(*args, **kwargs)
        if isinstance(oracle_result, RecoveryResult):
            postprocess_deepdiff(oracle_result.diff)
        return oracle_result

    return compare_system_equality_new


compare_system_equality = apply_postprocess_deepdiff(compare_system_equality)


def get_nondeterministic_fields(s1, s2, additional_exclude_paths):
    nondeterministic_fields = []
    result = compare_system_equality(s1, s2, additional_exclude_paths=additional_exclude_paths)
    if isinstance(result, RecoveryResult):
        diff = result.diff
        for diff_type, diffs in diff.items():
            if diff_type == 'dictionary_item_removed':
                for diff_field in diffs:
                    nondeterministic_fields.append(diff_field.path(output_format='list'))
            elif diff_type == 'dictionary_item_added':
                for diff_field in diffs:
                    nondeterministic_fields.append(diff_field.path(output_format='list'))
            elif diff_type == 'values_changed':
                for diff_field in diffs:
                    nondeterministic_fields.append(diff_field.path(output_format='list'))
            elif diff_type == 'type_changes':
                for diff_field in diffs:
                    nondeterministic_fields.append(diff_field.path(output_format='list'))
    return nondeterministic_fields


class TrialSingleInputIterator:
    def __init__(self, testcase_input: dict, testcase_hash: str):
        self.__history: List[Tuple[dict, dict]] = []
        self.__queuing_tests: List[Tuple[dict, dict]] = [
            (testcase_input, {'testcase': f'post_test_{testcase_hash}', 'field': None})]

    def __iter__(self) -> Generator[Tuple[dict, dict], None, None]:
        self.__history.append(self.__queuing_tests.pop())
        yield self.__history[0]

    @staticmethod
    def flush():
        unreachable()

    @staticmethod
    def revert():
        unreachable()

    @staticmethod
    def redo():
        unreachable()

    @staticmethod
    def swap_iterator(_: Iterator[Tuple[List[str], TestCase]]) -> Iterator[Tuple[List[str], TestCase]]:
        return iter(())

    @property
    def history(self) -> List[Tuple[dict, dict]]:
        return self.__history


def post_process_task(runner: 'PostDiffRunner', data: Tuple[dict, str, dict, Deploy]) -> Trial:
    system_input, system_input_hash, context, deploy = data
    collector = with_context(CollectorContext(
        namespace=context['namespace'],
        crd_meta_info=context['crd'],
    ), snapshot_collector)

    # Inject the deploy step into the collector, to deploy the operator before running the test
    collector = deploy.chain_with(drop_first_parameter(collector))

    trial = Trial(TrialSingleInputIterator(system_input, system_input_hash), None, num_mutation=10)
    return ray.get(runner.run.remote(trial, collector))


def post_diff_compare_task(runner: 'PostDiffRunner', data: Tuple[Snapshot, DataFrame, bool]) -> OracleResult:
    snapshot, originals, run_check_indeterministic = data
    return runner.check_trial.remote(snapshot, originals, run_check_indeterministic)


@ray.remote(scheduling_strategy="SPREAD", num_cpus=1, resources={"disk": 10})
class PostDiffRunner:
    def __init__(self, context: dict, deploy: Deploy, diff_ignore_fields: List[str], engine_class: Type[Engine],
                 engine_version: str, num_nodes: int, preload_images: List[str] = None,
                 preload_images_store: Callable[[str], str] = None):
        self.trial_runner = Runner.remote(engine_class, engine_version, num_nodes, preload_images, preload_images_store)
        self.context = context
        self.deploy = deploy
        self.diff_ignore_fields = diff_ignore_fields

    def run(self, trial: Trial, snapshot_collector: Callable[['Runner', Trial, dict], Snapshot])-> Trial:
        return self.trial_runner.run.remote(trial, snapshot_collector)

    def check_trial(self, diff_snapshot: Snapshot, originals: DataFrame, run_check_indeterministic: bool = False):
        group_errs = []
        diff_system_input = diff_snapshot.input
        digest = digest_input(diff_system_input)

        for _, original in originals.iterrows():
            snapshot: Snapshot = original['snapshot']
            gen = original['gen']

            if gen == 0:
                continue
            result = compare_system_equality(diff_snapshot.system_state,
                                             snapshot.system_state,
                                             additional_exclude_paths=self.diff_ignore_fields)
            if result.means(OracleControlFlow.ok):
                continue

            errored = False
            if run_check_indeterministic:
                additional_trial = post_process_task(self, (diff_system_input, digest, self.context, self.deploy))
                try:
                    additional_snapshot, _ = unpack_history_iterator_or_raise(additional_trial.history_iterator())
                except RuntimeError as e:
                    logging.error(str(e))
                    continue
                additional_snapshot: Snapshot
                indeterministic_fields = get_nondeterministic_fields(snapshot.system_state,
                                                                     additional_snapshot.system_state,
                                                                     self.diff_ignore_fields)
                result: RecoveryResult
                for delta_category in result.diff:
                    for delta in result.diff[delta_category]:
                        if delta.path(output_format='list') not in indeterministic_fields:
                            errored = True
                            break
            else:
                errored = True
            if errored:
                group_errs.append({
                    'digest': digest,
                    'id': original['trial'],
                    'gen': gen,
                    'diff_test': asdict(result),
                    'diff_test_status': ','.join(result.all_meanings()),
                    'input': original['snapshot'].input
                })
        return group_errs


def load_snapshots(workdir: str) -> Generator[Snapshot, None, None]:
    diff_files = glob.glob(os.path.join(workdir, '**', 'difftest-*.pkl'))
    for diff_file in diff_files:
        trial = pickle.load(open(diff_file, 'rb'))
        try:
            snapshot, _ = unpack_history_iterator_or_raise(trial.history_iterator())
        except RuntimeError as e:
            logging.error(str(e))
            continue
        yield snapshot


class PostDiffTest(PostProcessor):

    def __init__(self, trials: Dict[str, Trial], config: OperatorConfig, num_workers: int = 1):
        super().__init__(trials, config)
        logger = get_thread_logger(with_prefix=True)

        self.all_inputs = []
        for trial_path, trial in self._trials.items():
            for (gen, ((system_input, testcase_sig), exception_or_snapshot_plus_oracle_result)) in enumerate(
                    trial.history_iterator()):
                if isinstance(exception_or_snapshot_plus_oracle_result, Exception):
                    continue
                (snapshot, run_result) = exception_or_snapshot_plus_oracle_result
                if not all(map(lambda x: x.means(OracleControlFlow.ok), run_result)):
                    continue
                self.all_inputs.append({
                    'trial': trial_path,
                    'trial_object': trial,
                    'gen': gen,
                    'input': system_input,
                    'input_digest': digest_input(system_input),
                    'snapshot': snapshot,
                    'test_case_signature': testcase_sig,
                    'runtime_result': run_result,
                })

        self.df = pd.DataFrame(self.all_inputs,
                               columns=[
                                   'trial', 'trial_object', 'gen', 'input', 'input_digest', 'snapshot',
                                   'test_case_signature', 'runtime_result'
                               ])

        self.unique_inputs: Dict[str, DataFrame] = {}  # input digest -> group of steps
        groups = self.df.groupby('input_digest')
        for digest, group in groups:
            self.unique_inputs[digest] = group

        logger.info(f'Found {len(self.unique_inputs)} unique inputs')
        print(groups.count())
        series = groups.count().sort_values('trial', ascending=False)
        print(series.head())
        if num_workers:
            self._runners = ActorPool(
                [PostDiffRunner.remote(self._context, self._deploy, self.diff_ignore_fields, Kind, CONST.K8S_VERSION,
                                       config.num_nodes, self._context['preload_images']) for _ in range(num_workers)]
            )
        else:
            self._runners = None
        self.num_workers = num_workers

    def post_process(self, workdir: str):
        if not os.path.exists(workdir):
            os.mkdir(workdir)

        test_case_list = list(self.unique_inputs.items())
        while len(test_case_list) != 0:
            (digest, group) = test_case_list.pop()
            trial_name = group.iloc[0]['trial']
            if os.path.exists(os.path.join(workdir, trial_name, f'difftest-{digest}.pkl')):
                continue
            self._runners.submit(post_process_task, (group.iloc[0]['input'], group.iloc[0]['input_digest'], self._context, self._deploy))

        while self._runners.has_next():
            # As long as there are still runners running, or we have remaining test cases
            # we keep running
            trial = self._runners.get_next_unordered()

            try:
                snapshot, _ = unpack_history_iterator_or_raise(trial.history_iterator())
            except RuntimeError as e:
                logging.error(str(e))
                continue

            snapshot: Snapshot
            digest = digest_input(snapshot.input)

            trial_save_dir = self.unique_inputs[digest].iloc[0]['trial']
            trial_save_dir = os.path.join(workdir, trial_save_dir)
            os.makedirs(trial_save_dir, exist_ok=True)

            difftest_result = {
                'input_digest': digest,
                'snapshot': asdict(snapshot),
                'originals': self.unique_inputs[digest][['trial', 'gen']].to_dict('records'),
            }
            difftest_result_path = os.path.join(trial_save_dir, f'difftest-{digest}.json')
            with open(difftest_result_path, 'w') as f:
                json.dump(difftest_result, f, cls=ActoEncoder, indent=6)
            pickle.dump(trial, open(os.path.join(trial_save_dir, f'difftest-{digest}.pkl'), 'wb'))

    def check(self, workdir: str, run_check_indeterministic: bool = False):
        results = self.check_by_snapshots(load_snapshots(workdir), run_check_indeterministic)
        results_df = pd.DataFrame(results)
        results_df.to_csv(os.path.join(workdir, 'diff_test.csv'))
        pickle.dump(results, open(os.path.join(workdir, 'diff_test.pkl'), 'wb'))

    def check_by_snapshots(self, snapshots: Iterable[Snapshot], run_check_indeterministic: bool = False) -> List[OracleResult]:
        for snapshot in snapshots:
            digest = digest_input(snapshot.input)
            self._runners.submit(post_diff_compare_task,
                                 (snapshot, self.unique_inputs[digest], run_check_indeterministic))
        results = []
        while self._runners.has_next():
            result = self._runners.get_next_unordered()
            results.extend(result)
        return results



if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--testrun-dir', type=str, required=True)
    parser.add_argument('--workdir-path', type=str, required=True)
    parser.add_argument('--num-workers', type=int, default=1)
    parser.add_argument('--checkonly', action='store_true')
    args = parser.parse_args()

    # Register custom exception hook
    sys.excepthook = handle_excepthook
    threading.excepthook = thread_excepthook
    global notify_crash_
    notify_crash_ = True

    log_filename = 'check.log' if args.checkonly else 'test.log'
    os.makedirs(args.workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(args.workdir_path, log_filename),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    start = time.time()

    with open(args.config, 'r') as config_file:
        config = OperatorConfig(**json.load(config_file))
    trials = {}
    trial_paths = glob.glob(os.path.join(args.testrun_dir, '**', 'trial.pkl'))
    common_prefix = os.path.commonprefix(trial_paths)
    for trial_path in trial_paths:
        trials[trial_path[len(common_prefix):]] = pickle.load(open(trial_path, 'rb'))
    p = PostDiffTest(trials=trials, config=config, num_workers=args.num_workers)
    if not args.checkonly:
        p.post_process(args.workdir_path)
    p.check(args.workdir_path)

    logging.info(f'Total time: {time.time() - start} seconds')
