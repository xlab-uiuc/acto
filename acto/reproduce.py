import argparse
import functools
import json
import logging
import os
from datetime import datetime
from functools import partial
from glob import glob
from typing import List, Optional

import jsonpatch
import yaml

from acto import DEFAULT_KUBERNETES_VERSION
from acto.engine import Acto
from acto.input.input import DeterministicInputModel
from acto.input.testcase import TestCase
from acto.input.testplan import TestGroup
from acto.input.value_with_schema import ValueWithSchema
from acto.input.valuegenerator import extract_schema_with_value_generator
from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_diff_test import PostDiffTest
from acto.result import OracleResults
from acto.utils import get_thread_logger


def apply_repro_testcase(
    value_with_schema: ValueWithSchema,
    _: list,
    testcase: TestCase,
    __: bool = False,
) -> jsonpatch.JsonPatch:
    """apply_testcase function for reproducing"""
    logger = get_thread_logger(with_prefix=True)
    next_cr = testcase.mutator(None)  # next cr in yaml format

    prev = value_with_schema.raw_value()
    value_with_schema.update(next_cr)
    curr = value_with_schema.raw_value()
    logger.debug("current cr: %s", curr)

    patch = jsonpatch.make_patch(prev, curr)
    logger.info("JSON patch: %s", patch)
    return patch


def load_cr_from_trial(trial_dir: str) -> list:
    """Load mutated CRs from a trial directory
    Returns:
        list: list of mutated CRs
    """
    cr_list = []
    for mutated_file in sorted(glob(os.path.join(trial_dir, "mutated-*.yaml"))):
        with open(mutated_file, "r", encoding="utf-8") as f:
            cr_list.append(yaml.load(f, Loader=yaml.FullLoader))
    return cr_list


class CustomField:
    """Custom field for reproducing"""

    def __init__(self, path, schema) -> None:
        self.path = path
        self.custom_schema = schema


class ReproInputModel(DeterministicInputModel):
    """Input model for reproducing"""

    # pylint: disable=super-init-not-called, unused-argument
    def __init__(
        self,
        crd: dict,
        seed_input: dict,
        example_dir: str,
        num_workers: int,
        num_cases: int,
        reproduce_dir: str,
        mount: Optional[list] = None,
        kubernetes_version: str = DEFAULT_KUBERNETES_VERSION,
        custom_module_path: Optional[str] = None,
    ) -> None:
        logger = get_thread_logger(with_prefix=True)
        # WARNING: Not sure the initialization is correct
        # TODO: The line below need to be reviewed.
        self.root_schema = extract_schema_with_value_generator(
            [], crd["spec"]["versions"][-1]["schema"]["openAPIV3Schema"]
        )
        self.testcases = []
        cr_list = load_cr_from_trial(reproduce_dir)
        if len(cr_list) == 0:
            raise RuntimeError(
                f"No CRs found in {reproduce_dir}. CR file name should start with mutated-"
            )

        step = 1
        self.seed_input = cr_list[0]
        for cr in cr_list[1:]:
            cr_mutator = partial(repro_mutator, cr)
            t = TestCase(
                f"step-{step}", repro_precondition, cr_mutator, repro_setup
            )
            self.testcases.append(t)
            step += 1
        logger.info("%d steps for reproducing", len(self.testcases))
        self.num_total_cases = len(cr_list) - 1
        self.num_workers = 1
        self.metadata = {}

    def initialize(self, initial_value: dict):
        """Override"""

    def set_worker_id(self, worker_id: int):
        """Override"""

    def set_mode(self, mode: str):
        pass

    def is_empty(self):
        """If testcases are empty"""
        logger = get_thread_logger(with_prefix=True)
        logger.debug("testcases: %d", len(self.testcases))
        return len(self.testcases) == 0

    def get_seed_input(self) -> dict:
        return self.seed_input

    def generate_test_plan(
        self, delta_from: str = None, focus_fields: list = None
    ) -> dict:
        _ = delta_from
        _ = focus_fields
        return {}

    def next_test(self) -> list:
        """
        Returns:
            - a list of tuples, containing
              an empty TreeNode and a test case
        """
        test = self.testcases.pop(0)
        return [
            (TestGroup([test]), ('["spec"]', test))
        ]  # return the first test case

    def apply_k8s_schema(self, k8s_field):
        """Override"""


def repro_precondition(_):
    """Precondition for reproducing"""
    return True


def repro_mutator(cr, _):
    """Mutator for reproducing"""
    return cr


def repro_setup(_):
    """Setup for reproducing"""
    return None


def reproduce(
    workdir_path: str,
    reproduce_dir: str,
    operator_config: str,
    acto_namespace: int,
    **kwargs,
) -> List[OracleResults]:
    """Reproduce the trial folder"""
    os.makedirs(workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(workdir_path, "test.log"),
        level=logging.DEBUG,
        filemode="w",
        format="%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s",
    )
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    with open(operator_config, "r", encoding="utf-8") as config_file:
        config = OperatorConfig(**json.load(config_file))
    context_cache = os.path.join(
        os.path.dirname(config.seed_custom_resource), "context.json"
    )
    input_model = functools.partial(
        ReproInputModel, reproduce_dir=reproduce_dir
    )
    apply_testcase_f = apply_repro_testcase

    acto = Acto(
        workdir_path=workdir_path,
        operator_config=config,
        cluster_runtime=kwargs["cluster_runtime"],
        preload_images_=[],
        context_file=context_cache,
        helper_crd=None,
        num_workers=1,
        num_cases=1,
        dryrun=False,
        analysis_only=False,
        is_reproduce=True,
        input_model=input_model,
        apply_testcase_f=apply_testcase_f,
        acto_namespace=acto_namespace,
    )

    errors = acto.run(modes=["normal"])
    return [error for error in errors if error is not None]


def reproduce_postdiff(
    workdir_path: str,
    operator_config: str,
    acto_namespace: int,
    **kwargs,
) -> bool:
    """Reproduce the trial folder with post-diff test"""
    _ = kwargs
    with open(operator_config, "r", encoding="utf-8") as config_file:
        config = OperatorConfig(**json.load(config_file))
    post_diff_test_dir = os.path.join(workdir_path, "post_diff_test")
    logs = glob(workdir_path + "/*/operator-*.log")
    for log in logs:
        with open(log, "w", encoding="utf-8") as _:
            pass
    p = PostDiffTest(
        testrun_dir=workdir_path,
        config=config,
        ignore_invalid=True,
        acto_namespace=acto_namespace,
    )
    p.post_process(post_diff_test_dir, num_workers=1)
    p.check(post_diff_test_dir, num_workers=1)

    return (
        len(glob(os.path.join(post_diff_test_dir, "compare-results-*.json")))
        > 0
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automatic, Continuous Testing for k8s/openshift Operators"
    )
    parser.add_argument(
        "--reproduce-dir",
        dest="reproduce_dir",
        required=True,
        help="The directory of the trial folder to reproduce. "
        'CR files should have names starting with "mutated-"',
    )
    parser.add_argument(
        "--config", "-c", dest="config", help="Operator port config path"
    )
    parser.add_argument(
        "--cluster-runtime",
        "-r",
        dest="cluster_runtime",
        default="KIND",
        help="Cluster runtime for kubernetes, can be KIND (Default), K3D or MINIKUBE",
    )
    parser.add_argument(
        "--acto-namespace",
        dest="acto_namespace",
        default=0,
        help="Kubernetes namespace for acto",
    )
    parser.add_argument("--context", dest="context", help="Cached context data")
    args = parser.parse_args()

    workdir_path_ = f"testrun-{datetime.now().strftime('%Y-%m-%d-%H-%M')}"

    start_time = datetime.now()
    reproduce(
        workdir_path=workdir_path_,
        reproduce_dir=args.reproduce_dir,
        operator_config=args.config,
        acto_namespace=args.acto_namespace,
        cluster_runtime=args.cluster_runtime,
    )
    end_time = datetime.now()
