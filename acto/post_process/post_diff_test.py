import glob
import hashlib
import json
import logging
import multiprocessing
import os
import queue
import re
import subprocess
import sys
import threading
import time
from copy import deepcopy
from typing import Dict, List

import pandas as pd
from deepdiff import DeepDiff
from deepdiff.helper import CannotCompare
from deepdiff.model import DiffLevel
from deepdiff.operator import BaseOperator

sys.path.append('.')
sys.path.append('..')
from acto.common import (ErrorResult, PassResult, RecoveryResult, RunResult,
                         invalid_input_message_regex, kubernetes_client)
from acto.constant import CONST
from acto.deploy import Deploy, DeployMethod
from acto.kubernetes_engine import base, kind
from acto.runner import Runner
from acto.serialization import ActoEncoder
from acto.utils import (OperatorConfig, add_acto_label, get_thread_logger,
                        handle_excepthook, thread_excepthook)

from .post_process import PostProcessor, Step


def dict_hash(d: dict) -> int:
    '''Hash a dict'''
    return hash(json.dumps(d, sort_keys=True))

def compare_system_equality(curr_system_state: Dict,
                            prev_system_state: Dict,
                            additional_exclude_paths: List[str] = []):
    logger = get_thread_logger(with_prefix=False)
    curr_system_state = deepcopy(curr_system_state)
    prev_system_state = deepcopy(prev_system_state)

    try:
        del curr_system_state['endpoints']
        del prev_system_state['endpoints']
        del curr_system_state['job']
        del prev_system_state['job']
    except:
        return PassResult()

    # remove pods that belong to jobs from both states to avoid observability problem
    curr_pods = curr_system_state['pod']
    prev_pods = prev_system_state['pod']

    new_pods = {}
    for k, v in curr_pods.items():
        if 'metadata' in v and 'owner_references' in v[
            'metadata'] and v['metadata']['owner_references'] != None and v['metadata'][
            'owner_references'][0]['kind'] != 'Job':
            new_pods[k] = v
    curr_system_state['pod'] = new_pods

    new_pods = {}
    for k, v in prev_pods.items():
        if 'metadata' in v and 'owner_references' in v[
            'metadata'] and v['metadata']['owner_references'] != None and v['metadata'][
            'owner_references'][0]['kind'] != 'Job':
            new_pods[k] = v
    prev_system_state['pod'] = new_pods

    for name, obj in prev_system_state['secret'].items():
        if 'data' in obj and obj['data'] != None:
            for key, data in obj['data'].items():
                try:
                    obj['data'][key] = json.loads(data)
                except:
                    pass

    for name, obj in curr_system_state['secret'].items():
        if 'data' in obj and obj['data'] != None:
            for key, data in obj['data'].items():
                try:
                    obj['data'][key] = json.loads(data)
                except:
                    pass
    
    if len(curr_system_state['secret']) != len(prev_system_state['secret']):
        logger.debug(f"failed attempt recovering to seed state - secret count mismatch")
        return RecoveryResult(
            delta=DeepDiff(len(curr_system_state['secret']), len(prev_system_state['secret'])), 
            from_=prev_system_state, to_=curr_system_state)

    # remove custom resource from both states
    curr_system_state.pop('custom_resource_spec', None)
    prev_system_state.pop('custom_resource_spec', None)
    curr_system_state.pop('custom_resource_status', None)
    prev_system_state.pop('custom_resource_status', None)
    curr_system_state.pop('pvc', None)
    prev_system_state.pop('pvc', None)

    # remove fields that are not deterministic
    exclude_paths = [
        r".*\['metadata'\]\['managed_fields'\]",
        r".*\['metadata'\]\['cluster_name'\]",
        r".*\['metadata'\]\['creation_timestamp'\]",
        r".*\['metadata'\]\['resource_version'\]",
        r".*\['metadata'\].*\['uid'\]",
        r".*\['metadata'\]\['generation'\]$",
        r".*\['metadata'\]\['annotations'\]\['.*last-applied.*'\]",
        r".*\['metadata'\]\['annotations'\]\['.*\.kubernetes\.io.*'\]",
        r".*\['metadata'\]\['labels'\]\['.*revision.*'\]",
        r".*\['metadata'\]\['labels'\]\['owner-rv'\]",
        r".*\['status'\]",
        r"\['metadata'\]\['deletion_grace_period_seconds'\]",
        r"\['metadata'\]\['deletion_timestamp'\]",
        r".*\['spec'\]\['init_containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['volumes'\]\[.*\]\['name'\]$",
        r".*\[.*\]\['node_name'\]$",
        r".*\[\'spec\'\]\[\'host_users\'\]$",
        r".*\[\'spec\'\]\[\'os\'\]$",
        r".*\[\'grpc\'\]$",
        r".*\[\'spec\'\]\[\'volume_name\'\]$",
        r".*\['version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['uid'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['resource_version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['ip'\]",
        r".*\['cluster_ip'\]$",
        r".*\['cluster_i_ps'\].*$",
        r".*\['deployment_pods'\].*\['metadata'\]\['name'\]$",
        r"\[\'config_map\'\]\[\'kube\-root\-ca\.crt\'\]\[\'data\'\]\[\'ca\.crt\'\]$",
        r".*\['secret'\].*$",
        r"\['secrets'\]\[.*\]\['name'\]",
        r".*\['node_port'\]",
        r".*\['metadata'\]\['generate_name'\]",
        r".*\['metadata'\]\['labels'\]\['pod\-template\-hash'\]",
        r"\['deployment_pods'\].*\['metadata'\]\['owner_references'\]\[.*\]\['name'\]",
    ]

    exclude_paths.extend(additional_exclude_paths)

    diff = DeepDiff(
        prev_system_state,
        curr_system_state,
        exclude_regex_paths=exclude_paths,
        iterable_compare_func=compare_func,
        custom_operators=[
            NameOperator(r".*\['name'\]$"),
            TypeChangeOperator(r".*\['annotations'\]$")
        ],
        view='tree',
    )

    postprocess_deepdiff(diff)

    if diff:
        logger.debug(f"failed attempt recovering to seed state - system state diff: {diff}")
        return RecoveryResult(delta=diff, from_=prev_system_state, to_=curr_system_state)

    return PassResult()


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

    def give_up_diffing(self, level, diff_instance):
        x_name = level.t1
        y_name = level.t2
        if x_name == None or y_name == None:
            return False
        if re.search(r"^.+-([A-Za-z0-9]{5})$", x_name) and re.search(r"^.+-([A-Za-z0-9]{5})$",
                                                                     y_name):
            return x_name[:5] == y_name[:5]
        return False


class TypeChangeOperator(BaseOperator):

    def give_up_diffing(self, level, diff_instance):
        if level.t1 == None:
            if isinstance(level.t2, dict):
                level.t1 = {}
            elif isinstance(level.t2, list):
                level.t1 = []
        elif level.t2 == None:
            if isinstance(level.t1, dict):
                logging.info('t2 is None, t1 is dict')
                level.t2 = {}
            elif isinstance(level.t1, list):
                level.t2 = []
        return False



def get_nondeterministic_fields(s1, s2, additional_exclude_paths):
    nondeterministic_fields = []
    result = compare_system_equality(s1, s2, additional_exclude_paths=additional_exclude_paths)
    if isinstance(result, RecoveryResult):
        diff = result.delta
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


class AdditionalRunner:

    def __init__(self, context: Dict, deploy: Deploy, workdir: str, cluster: base.KubernetesEngine,
                 worker_id):

        self._context = context
        self._deploy = deploy
        self._workdir = workdir
        self._cluster = cluster
        self._worker_id = worker_id
        self._cluster_name = f"acto-cluster-{worker_id}"
        self._context_name = cluster.get_context_name(f"acto-cluster-{worker_id}")
        self._kubeconfig = os.path.join(os.path.expanduser('~'), '.kube', self._context_name)
        self._generation = 0

    def run_cr(self, cr, trial, gen):
        self._cluster.restart_cluster(self._cluster_name, self._kubeconfig, CONST.K8S_VERSION)
        apiclient = kubernetes_client(self._kubeconfig, self._context_name)
        deployed = self._deploy.deploy_with_retry(self._context, self._kubeconfig,
                                                  self._context_name)
        add_acto_label(apiclient, self._context)
        trial_dir = os.path.join(self._workdir, 'trial-%02d' % self._worker_id)
        os.makedirs(trial_dir, exist_ok=True)
        runner = Runner(self._context, trial_dir, self._kubeconfig, self._context_name)
        snapshot, err = runner.run(cr, generation=self._generation)
        difftest_result = {
            'input_digest': hashlib.md5(json.dumps(cr, sort_keys=True).encode("utf-8")).hexdigest(),
            'snapshot': snapshot.to_dict(),
            'originals': {
                'trial': trial,
                'gen': gen,
            },
        }
        difftest_result_path = os.path.join(trial_dir, 'difftest-%03d.json' % self._generation)
        with open(difftest_result_path, 'w') as f:
            json.dump(difftest_result, f, cls=ActoEncoder, indent=6)

        return snapshot


class DeployRunner:

    def __init__(self, workqueue: multiprocessing.Queue, context: Dict, deploy: Deploy,
                 workdir: str, cluster: base.KubernetesEngine, worker_id):
        self._workqueue = workqueue
        self._context = context
        self._deploy = deploy
        self._workdir = workdir
        self._cluster = cluster
        self._worker_id = worker_id
        self._cluster_name = f"acto-cluster-{worker_id}"
        self._context_name = cluster.get_context_name(f"acto-cluster-{worker_id}")
        self._kubeconfig = os.path.join(os.path.expanduser('~'), '.kube', self._context_name)
        self._images_archive = os.path.join(workdir, 'images.tar')

    def run(self):
        logger = get_thread_logger(with_prefix=True)
        generation = 0
        trial_dir = os.path.join(self._workdir, 'trial-%02d' % self._worker_id)
        os.makedirs(trial_dir, exist_ok=True)

        # Start the cluster and deploy the operator
        self._cluster.restart_cluster(self._cluster_name, self._kubeconfig, CONST.K8S_VERSION)
        self._cluster.load_images(self._images_archive, self._cluster_name)
        apiclient = kubernetes_client(self._kubeconfig, self._context_name)
        deployed = self._deploy.deploy_with_retry(self._context, self._kubeconfig,
                                                  self._context_name)
        add_acto_label(apiclient, self._context)

        trial_dir = os.path.join(self._workdir, 'trial-%02d' % self._worker_id)
        os.makedirs(trial_dir, exist_ok=True)
        runner = Runner(self._context, trial_dir, self._kubeconfig, self._context_name)
        while True:
            try:
                group = self._workqueue.get(block=False)
            except queue.Empty:
                break

            cr = group.iloc[0]['input']

            snapshot, err = runner.run(cr, generation=generation)
            err = True
            difftest_result = {
                'input_digest': group.iloc[0]['input_digest'],
                'snapshot': snapshot.to_dict(),
                'originals': group[['trial', 'gen']].to_dict('records'),
            }
            difftest_result_path = os.path.join(trial_dir, 'difftest-%03d.json' % generation)
            with open(difftest_result_path, 'w') as f:
                json.dump(difftest_result, f, cls=ActoEncoder, indent=6)

            if err:
                logger.error(f'Restart cluster due to error: {err}')
                # Start the cluster and deploy the operator
                self._cluster.restart_cluster(self._cluster_name, self._kubeconfig,
                                              CONST.K8S_VERSION)
                apiclient = kubernetes_client(self._kubeconfig, self._context_name)
                deployed = self._deploy.deploy_with_retry(self._context, self._kubeconfig,
                                                          self._context_name)
                add_acto_label(apiclient, self._context)
                runner = Runner(self._context, trial_dir, self._kubeconfig, self._context_name)

            generation += 1


class PostDiffTest(PostProcessor):

    def __init__(self, testrun_dir: str, config: OperatorConfig, ignore_invalid: bool = False):
        super().__init__(testrun_dir, config)
        logger = get_thread_logger(with_prefix=True)

        self.all_inputs = []
        for trial, steps in self.trial_to_steps.items():
            for step in steps:
                invalid, _ = step.runtime_result.is_invalid()
                if invalid and not ignore_invalid:
                    continue
                self.all_inputs.append({
                    'trial': trial,
                    'gen': step.gen,
                    'input': step.input,
                    'input_digest': step.input_digest,
                    'operator_log': step.operator_log,
                    'system_state': step.system_state,
                    'cli_output': step.cli_output,
                    'runtime_result': step.runtime_result
                })

        self.df = pd.DataFrame(self.all_inputs,
                               columns=[
                                   'trial', 'gen', 'input', 'input_digest', 'operator_log',
                                   'system_state', 'cli_output', 'runtime_result'
                               ])

        self.unique_inputs: Dict[str, object] = {}  # input digest -> group of steps
        groups = self.df.groupby('input_digest')
        for digest, group in groups:
            self.unique_inputs[digest] = group

        logger.info(f'Found {len(self.unique_inputs)} unique inputs')
        print(groups.count())
        series = groups.count().sort_values('trial', ascending=False)
        print(series.head())

    def post_process(self, workdir: str, num_workers: int = 1):
        if not os.path.exists(workdir):
            os.mkdir(workdir)
        cluster = kind.Kind()
        cluster.configure_cluster(self.config.num_nodes, CONST.K8S_VERSION)
        deploy = Deploy(DeployMethod.YAML, self.config.deploy.file, self.config.deploy.init).new()
        # Build an archive to be preloaded
        images_archive = os.path.join(workdir, 'images.tar')
        if len(self.context['preload_images']) > 0:
            # first make sure images are present locally
            for image in self.context['preload_images']:
                subprocess.run(['docker', 'pull', image])
            subprocess.run(['docker', 'image', 'save', '-o', images_archive] +
                           list(self.context['preload_images']))
            
        workqueue = multiprocessing.Queue()
        for unique_input_group in self.unique_inputs.values():
            workqueue.put(unique_input_group)

        runners: List[DeployRunner] = []
        for i in range(num_workers):
            runner = DeployRunner(workqueue, self.context, deploy, workdir, cluster, i)
            runners.append(runner)

        processes = []
        for runner in runners:
            p = multiprocessing.Process(target=runner.run)
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    def check(self, workdir: str, num_workers: int = 1):
        logger = get_thread_logger(with_prefix=True)
        logger.info('Additional exclude paths: %s' % self.config.diff_ignore_fields)
        trial_dirs = glob.glob(os.path.join(workdir, 'trial-*'))

        workqueue = multiprocessing.Queue()
        for trial_dir in trial_dirs:
            for diff_test_result_path in glob.glob(os.path.join(trial_dir, 'difftest-*.json')):
                workqueue.put(diff_test_result_path)

        processes = []
        for i in range(num_workers):
            p = multiprocessing.Process(target=self.check_diff_test_result,
                                        args=(workqueue, workdir, i))
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

    def check_diff_test_result(self, workqueue: multiprocessing.Queue, workdir: str,
                               worker_id: int):
        logger = get_thread_logger(with_prefix=True)

        generation = 0  # for additional runner
        additional_runner_dir = os.path.join(workdir, f'additional-runner-{worker_id}')
        cluster = kind.Kind()
        cluster.configure_cluster(self.config.num_nodes, CONST.K8S_VERSION)

        deploy = Deploy(DeployMethod.YAML, self.config.deploy.file, self.config.deploy.init).new()

        runner = AdditionalRunner(context=self.context,
                                  deploy=deploy,
                                  workdir=additional_runner_dir,
                                  cluster=cluster,
                                  worker_id=worker_id)

        while True:
            try:
                diff_test_result_path = workqueue.get(block=False)
            except queue.Empty:
                break

            with open(diff_test_result_path, 'r') as f:
                diff_test_result = json.load(f)
            originals = diff_test_result['originals']

            group_errs = []
            for original in originals:
                trial = original['trial']
                gen = original['gen']

                if gen == 0:
                    continue

                trial_basename = os.path.basename(trial)
                original_result = self.trial_to_steps[trial_basename][gen]
                step_result = PostDiffTest.check_diff_test_step(diff_test_result, original_result,
                                                                self.config, False, runner)
                if step_result is None:
                    continue
                else:
                    group_errs.append(step_result)
            if len(group_errs) > 0:
                with open(
                        os.path.join(workdir,
                                     f'compare-results-{diff_test_result["input_digest"]}.json'),
                        'w') as result_f:
                    json.dump(group_errs, result_f, cls=ActoEncoder, indent=6)

        return None

    def check_diff_test_step(diff_test_result: Dict,
                             original_result: Step,
                             config: OperatorConfig,
                             run_check_indeterministic: bool = False,
                             additional_runner: AdditionalRunner = None) -> RecoveryResult:
        logger = get_thread_logger(with_prefix=True)
        trial_dir = original_result.trial_dir
        gen = original_result.gen

        if isinstance(original_result.runtime_result.health_result, ErrorResult):
            return

        original_operator_log = original_result.operator_log
        if invalid_input_message_regex(original_operator_log):
            return

        original_system_state = original_result.system_state
        result = compare_system_equality(diff_test_result['snapshot']['system_state'],
                                         original_system_state, config.diff_ignore_fields)
        if isinstance(result, PassResult):
            logger.info(f'Pass diff test for trial {trial_dir} gen {gen}')
            return None
        elif run_check_indeterministic:
            add_snapshot = additional_runner.run_cr(diff_test_result['snapshot']['input'],
                                                    trial_dir, gen)
            indeterministic_fields = get_nondeterministic_fields(original_system_state,
                                                                 add_snapshot.system_state,
                                                                 config.diff_ignore_fields)

            if len(indeterministic_fields) > 0:
                logger.info(f'Got additional nondeterministic fields: {indeterministic_fields}')
                for delta_category in result.delta:
                    for delta in result.delta[delta_category]:
                        if delta.path(output_format='list') not in indeterministic_fields:
                            logger.error(f'Fail diff test for trial {trial_dir} gen {gen}')
                            error_result = result.to_dict()
                            error_result['trial'] = trial_dir
                            error_result['gen'] = gen
                            return error_result
            else:
                logger.error(f'Fail diff test for trial {trial_dir} gen {gen}')
                error_result = result.to_dict()
                error_result['trial'] = trial_dir
                error_result['gen'] = gen
                return error_result
        else:
            logger.error(f'Fail diff test for trial {trial_dir} gen {gen}')
            error_result = result.to_dict()
            error_result['trial'] = trial_dir
            error_result['gen'] = gen
            return error_result


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
    p = PostDiffTest(testrun_dir=args.testrun_dir, config=config)
    if not args.checkonly:
        p.post_process(args.workdir_path, num_workers=args.num_workers)
    p.check(args.workdir_path, num_workers=args.num_workers)

    logging.info(f'Total time: {time.time() - start} seconds')