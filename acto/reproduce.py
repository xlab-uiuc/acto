import argparse
from datetime import datetime
import json
import logging
from typing import Generator, Tuple, List, Iterator
from glob import glob
import os

import yaml

# TODO add main function
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
    parser.add_argument(
        '--reproduce-dir',
        dest='reproduce_dir',
        required=True,
        help='The directory of the trial folder to reproduce. CR files should have names starting with "mutated-"'
    )
    parser.add_argument('--config', '-c', dest='config', help='Operator port config path')
    parser.add_argument(
        '--cluster-runtime',
        '-r',
        dest='cluster_runtime',
        default="KIND",
        help='Cluster runtime for kubernetes, can be KIND (Default), K3D or MINIKUBE')
    parser.add_argument('--context', dest='context', help='Cached context data')
    args = parser.parse_args()

    from acto.lib.monkey_patch_loader import load_monkey_patch
    load_monkey_patch(args.config)

    from acto.engine_new import Acto
    from acto.input import TestCase
    from acto.utils import get_thread_logger
    from acto.lib.operator_config import OperatorConfig


    class ReproduceTrialInputIterator:
        def __init__(self, system_inputs: List[dict]):
            self._system_inputs = system_inputs
            self._history = []

        def __iter__(self) -> Generator[Tuple[dict, dict], None, None]:
            for (gen, system_input) in enumerate(self._system_inputs):
                self._history.append((system_input, {
                    "testcase": f'reproduce-gen-{gen}',
                    "field": None
                }))
                yield self._history[-1]

        def flush(self):
            pass

        def revert(self):
            pass

        def swap_iterator(self, _: Iterator[Tuple[List[str], 'TestCase']]) -> Iterator[Tuple[List[str], 'TestCase']]:
            return iter(())

        @property
        def history(self) -> List[Tuple[dict, dict]]:
            return self._history


    def reproduce(workdir_path: str, reproduce_dir: str, operator_config: str, **kwargs):
        with open(operator_config, 'r') as config_file:
            config = OperatorConfig(**json.load(config_file))
        context_cache = os.path.join(os.path.dirname(config.seed_custom_resource), 'context.json')

        acto = Acto(workdir_path=workdir_path,
                    operator_config=config,
                    cluster_runtime=kwargs['cluster_runtime'],
                    enable_analysis=True,
                    preload_images_=[],
                    context_file=context_cache,
                    helper_crd=None,
                    num_workers=1,
                    num_cases=1,
                    dryrun=False,
                    analysis_only=False,
                    is_reproduce=False,
                    reproduce_dir=reproduce_dir)

        system_input_paths = glob(os.path.join(reproduce_dir, 'mutated-*.yaml'))
        system_input_paths = sorted(system_input_paths, key=lambda p: p.replace('--1', '-a'))
        system_inputs = list(map(yaml.safe_load, map(open, system_input_paths)))
        acto.run_trials([ReproduceTrialInputIterator(system_inputs)])

    workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')
    os.makedirs(workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format='%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s')
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    logger = get_thread_logger(with_prefix=False)

    start_time = datetime.now()
    reproduce(workdir_path=workdir_path,
              reproduce_dir=args.reproduce_dir,
              operator_config=args.config,
              cluster_runtime=args.cluster_runtime)
    end_time = datetime.now()
    logger.info('Acto finished in %s', end_time - start_time)
