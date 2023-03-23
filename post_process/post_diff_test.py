import json
import logging
import multiprocessing
import os
import queue
import sys
from typing import Dict, List
import pandas as pd

sys.path.append('.')
sys.path.append('..')
from constant import CONST
from thread_logger import get_thread_logger
from common import ActoEncoder, OperatorConfig, kubernetes_client
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

        print(groups.count())
        series = groups.count().sort_values('trial', ascending=False)
        print(series.head())

    def post_process(self, workdir: str, num_workers: int = 1):
        cluster = kind.Kind()
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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--testrun-dir', type=str, required=True)
    parser.add_argument('--workdir-path', type=str, required=True)
    args = parser.parse_args()

    os.makedirs(args.workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(args.workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    with open(args.config, 'r') as config_file:
        config = OperatorConfig(**json.load(config_file))
    p = PostDiffTest(testrun_dir=args.testrun_dir,
                     config=config)
    p.post_process(args.workdir_path)