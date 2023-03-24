import glob
import json
import logging
import multiprocessing
import os
import queue
import sys
import threading
import time
from typing import Dict, List
import pandas as pd

sys.path.append('.')
sys.path.append('..')
from acto import handle_excepthook, thread_excepthook
from constant import CONST
from checker import compare_system_equality
from thread_logger import get_thread_logger
from common import ActoEncoder, ErrorResult, OperatorConfig, PassResult, kubernetes_client
from runner import Runner
from deploy import Deploy, DeployMethod
from k8s_cluster import base, kind
from preprocess import add_acto_label
from .post_process import PostProcessor


def dict_hash(d: dict) -> int:
    '''Hash a dict'''
    return hash(json.dumps(d, sort_keys=True))


class DeployRunner:

    def __init__(self, workqueue: multiprocessing.Queue, context: Dict, deploy: Deploy,
                 workdir: str, cluster: base.KubernetesCluster, worker_id):
        self._workqueue = workqueue
        self._context = context
        self._deploy = deploy
        self._workdir = workdir
        self._cluster = cluster
        self._worker_id = worker_id
        self._cluster_name = f"acto-cluster-{worker_id}"
        self._kubeconfig = os.path.join(os.path.expanduser('~'), '.kube', self._cluster_name)
        self._context_name = cluster.get_context_name(f"acto-cluster-{worker_id}")

    def run(self):
        logger = get_thread_logger(with_prefix=True)
        generation = 0
        trial_dir = os.path.join(self._workdir, 'trial-%02d' % self._worker_id)
        os.makedirs(trial_dir, exist_ok=True)

        # Start the cluster and deploy the operator
        self._cluster.restart_cluster(self._cluster_name, self._kubeconfig, CONST.K8S_VERSION)
        apiclient = kubernetes_client(self._kubeconfig, self._context_name)
        deployed = self._deploy.deploy_with_retry(self._context, self._kubeconfig,
                                                  self._context_name)
        add_acto_label(apiclient, self._context)

        trial_dir = os.path.join(self._workdir, 'trial-%02d' % self._worker_id)
        os.makedirs(trial_dir, exist_ok=True)
        while True:
            try:
                group = self._workqueue.get(block=False)
            except queue.Empty:
                break

            cr = group.iloc[0]['input']
            runner = Runner(self._context, trial_dir, self._kubeconfig, self._context_name)

            snapshot, err = runner.run(cr, generation=generation)
            err = runner.delete(generation=generation)
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

            generation += 1


class PostDiffTest(PostProcessor):

    def __init__(self, testrun_dir: str, config: OperatorConfig):
        super().__init__(testrun_dir, config)
        logger = get_thread_logger(with_prefix=True)

        self.all_inputs = []
        for trial, steps in self.trial_to_steps.items():
            for step in steps:
                invalid, _ = step.runtime_result.is_invalid()
                if invalid:
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
        groups = self.df.groupby(['input_digest'])
        for digest, group in groups:
            self.unique_inputs[digest] = group

        logger.info(f'Found {len(self.unique_inputs)} unique inputs')
        print(groups.count())
        series = groups.count().sort_values('trial', ascending=False)
        print(series.head())

    def post_process(self, workdir: str, num_workers: int = 1):
        cluster = kind.Kind()
        cluster.configure_cluster(self.config.num_nodes, CONST.K8S_VERSION)
        deploy = Deploy(DeployMethod.YAML, self.config.deploy.file, self.config.deploy.init).new()
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

    def check(self, workdir: str):
        logger = get_thread_logger(with_prefix=True)
        logger.info('Additional exclude paths: %s' % self.config.diff_ignore_fields)
        trial_dirs = glob.glob(os.path.join(workdir, 'trial-*'))

        with open(os.path.join(workdir, 'compare_results.json'), 'w') as result_f:
            for trial_dir in trial_dirs:
                for diff_test_result_path in glob.glob(os.path.join(trial_dir, 'difftest-*.json')):
                    with open(diff_test_result_path, 'r') as f:
                        diff_test_result = json.load(f)
                        error = self.check_diff_test_result(diff_test_result)
                        if error:
                            result_f.write(json.dumps(error.to_dict(), cls=ActoEncoder, indent=6))

    def check_diff_test_result(self, diff_test_result: Dict):
        logger = get_thread_logger(with_prefix=True)
        snapshot = diff_test_result['snapshot']
        originals = diff_test_result['originals']

        for original in originals:
            trial = original['trial']
            gen = original['gen']

            if isinstance(self.trial_to_steps[trial][gen].runtime_result.health_result, ErrorResult):
                continue
            original_system_state = self.trial_to_steps[trial][gen].system_state
            result = compare_system_equality(snapshot['system_state'], original_system_state,
                                             self.config.diff_ignore_fields)
            if isinstance(result, PassResult):
                logger.info(f'Pass diff test for trial {trial} gen {gen}')
            else:
                logger.error(f'Fail diff test for trial {trial} gen {gen}')
                logger.error(result)
                return result

        return None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--testrun-dir', type=str, required=True)
    parser.add_argument('--workdir-path', type=str, required=True)
    parser.add_argument('--num-workers', type=int, default=1)
    args = parser.parse_args()

    # Register custom exception hook
    sys.excepthook = handle_excepthook
    threading.excepthook = thread_excepthook
    global notify_crash_
    notify_crash_ = True

    os.makedirs(args.workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(args.workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    start = time.time()

    with open(args.config, 'r') as config_file:
        config = OperatorConfig(**json.load(config_file))
    p = PostDiffTest(testrun_dir=args.testrun_dir, config=config)
    p.post_process(args.workdir_path, num_workers=args.num_workers)
    p.check(args.workdir_path)

    logging.info(f'Total time: {time.time() - start} seconds')