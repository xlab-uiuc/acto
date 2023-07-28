import argparse
import glob
import json
import multiprocessing
import os
import logging
import pickle
import random
import time

from acto.config import actoConfig
import acto.config as acto_config
acto_config.load_config(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     'config_post_diff_test.yaml'))

from acto.lib.monkey_patch_loader import load_monkey_patch
from acto.lib.operator_config import OperatorConfig
from acto.post_process import PostDiffTest

# for debugging, set random seed to 0
random.seed(0)
multiprocessing.set_start_method('fork')

parser = argparse.ArgumentParser(
    description='Automatic, Continuous Testing for k8s/openshift Operators')
parser.add_argument('--workdir',
                    dest='workdir_path',
                    type=str,
                    help='Working directory')
parser.add_argument('--config', '-c', dest='config', help='Operator port config path')
parser.add_argument('--num-workers',
                    dest='num_workers',
                    type=int,
                    default=1,
                    help='Number of concurrent workers to run Acto with')
parser.add_argument('--checkonly', action='store_true')

args = parser.parse_args()

with open(args.config, 'r') as config_file:
    config = OperatorConfig(**json.load(config_file))
load_monkey_patch(config)

os.makedirs(args.workdir_path, exist_ok=True)
# Setting up log infra
logging.basicConfig(
    filename=os.path.join(args.workdir_path, 'test.log'),
    level=logging.DEBUG,
    filemode='w',
    format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
logging.getLogger("kubernetes").setLevel(logging.ERROR)
logging.getLogger("sh").setLevel(logging.ERROR)
if actoConfig.parallel.executor == 'ray':
    import ansible_runner
    import ray

    ansible_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'ansible')
    ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                       playbook=os.path.join(ansible_dir, 'acto_ray.yaml'))
    head_result = ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                                     playbook=os.path.join(ansible_dir, 'ray_head.yaml'))
    ansible_runner.run(inventory=actoConfig.parallel.ansible_inventory,
                       playbook=os.path.join(ansible_dir, 'ray_worker.yaml'))
    if head_result.stats['changed'] != {}:
        time.sleep(5)
    ray.init(address='auto')


def main():
    post_diff_test_dir = os.path.join(args.workdir_path, 'post_diff_test')
    trials = {}
    trial_paths = glob.glob(os.path.join(args.workdir_path, '**', 'trial.pkl'))
    common_prefix = trial_paths[0][trial_paths[0].find('trial-'):] if len(trial_paths) == 1 else os.path.commonpath(
        trial_paths) + os.path.sep
    for trial_path in trial_paths:
        trials[trial_path[len(common_prefix):][:-len('/trial.pkl')]] = pickle.load(open(trial_path, 'rb'))
    p = PostDiffTest(trials=trials, config=config, num_workers=args.num_workers)
    if not args.checkonly:
        p.post_process(post_diff_test_dir)
    p.check(post_diff_test_dir)
    p.teardown()


if __name__ == '__main__':
    main()
    logging.info('Acto finished')
