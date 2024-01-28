import argparse
import importlib
import json
import logging
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime

random.seed(0)

start_time = time.time()
workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')

parser = argparse.ArgumentParser(
    description='Automatic, Continuous Testing for k8s/openshift Operators')
parser.add_argument('--workdir',
                    dest='workdir_path',
                    type=str,
                    default=workdir_path,
                    help='Working directory')
parser.add_argument('--config', '-c', dest='config', help='Operator port config path')
parser.add_argument(
    '--cluster-runtime',
    '-r',
    dest='cluster_runtime',
    default="KIND",
    help='Cluster runtime for kubernetes, can be KIND (Default), K3D or MINIKUBE')
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

parser.add_argument('--additional-semantic',
                    dest='additional_semantic',
                    action='store_true',
                    help='Run additional semantic testcases')
parser.add_argument('--delta-from', dest='delta_from', help='Delta from')
parser.add_argument('--notify-crash',
                    dest='notify_crash',
                    action='store_true',
                    help='Submit a google form response to notify')
parser.add_argument('--learn-analysis',
                    dest='learn_analysis_only',
                    action='store_true',
                    help='Only learn analysis')
parser.add_argument('--dryrun',
                    dest='dryrun',
                    action='store_true',
                    help='Only generate test cases without executing them')
parser.add_argument('--checkonly', action='store_true')

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
    config = json.load(config_file)
    if 'monkey_patch' in config:
        importlib.import_module(config['monkey_patch'])

from acto import common
from acto.engine import Acto, apply_testcase
from acto.input.input import DeterministicInputModel, InputModel
from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_diff_test import PostDiffTest
from acto.utils.error_handler import handle_excepthook, thread_excepthook
from acto.utils.thread_logger import get_thread_logger

logger = get_thread_logger(with_prefix=False)

# Register custom exception hook
sys.excepthook = handle_excepthook
threading.excepthook = thread_excepthook

if args.notify_crash:
    logger.critical('Crash notification should be enabled in config.yaml')

with open(args.config, 'r') as config_file:
    config = json.load(config_file)
    if 'monkey_patch' in config:
        del config['monkey_patch']
    config = OperatorConfig(**config)
logger.info('Acto started with [%s]' % sys.argv)
logger.info('Operator config: %s', config)

# Preload frequently used images to amid ImagePullBackOff
if args.preload_images:
    logger.info('%s will be preloaded into Kind cluster', args.preload_images)

# register timeout to automatically stop after # hours
if args.duration != None:
    signal.signal(signal.SIGALRM, common.timeout_handler)
    signal.alarm(int(args.duration) * 60 * 60)

if args.context == None:
    context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')
else:
    context_cache = args.context

# Initialize input model and the apply testcase function
# input_model = InputModel(context_cache['crd']['body'], config.example_dir,
#   args.num_workers, args.num_cases, None)
input_model = DeterministicInputModel
apply_testcase_f = apply_testcase
is_reproduce = False

start_time = datetime.now()
acto = Acto(workdir_path=args.workdir_path,
            operator_config=config,
            cluster_runtime=args.cluster_runtime,
            preload_images_=args.preload_images,
            context_file=context_cache,
            helper_crd=args.helper_crd,
            num_workers=args.num_workers,
            num_cases=args.num_cases,
            dryrun=args.dryrun,
            analysis_only=args.learn_analysis_only,
            is_reproduce=is_reproduce,
            input_model=input_model,
            apply_testcase_f=apply_testcase_f,
            delta_from=args.delta_from,
            focus_fields=config.focus_fields,)
generation_time = datetime.now()
logger.info('Acto initialization finished in %s', generation_time - start_time)
if args.additional_semantic:
    acto.run(modes=[InputModel.ADDITIONAL_SEMANTIC])
elif not args.learn:
    acto.run(modes=['normal'])
normal_finish_time = datetime.now()
logger.info('Acto normal run finished in %s', normal_finish_time - start_time)
logger.info('Start post processing steps')

# Post processing
post_diff_test_dir = os.path.join(args.workdir_path, 'post_diff_test')
p = PostDiffTest(testrun_dir=args.workdir_path, config=config)
if not args.checkonly:
    p.post_process(post_diff_test_dir, num_workers=args.num_workers)
p.check(post_diff_test_dir, num_workers=args.num_workers)

end_time = datetime.now()
logger.info('Acto end to end finished in %s', end_time - start_time)