import glob
import json
import os
from collections import defaultdict
from typing import Dict, Optional, Tuple

import pytest
import yaml
from deepdiff.helper import NotPresent

from acto.checker.impl.consistency import ConsistencyChecker
from acto.checker.impl.tests import load_snapshot
from acto.common import Diff, PropertyPath
from acto.input import DeterministicInputModel
from acto.result import (
    ConsistencyOracleResult,
    InvalidInputResult,
    OracleResult,
)
from acto.snapshot import Snapshot


def input_model_and_context_mapping() -> (
    Dict[str, Tuple[Dict, DeterministicInputModel]]
):
    """Returns a mapping from apiVersion to (context, input_model)"""
    configs = glob.glob("./data/**/config.json")
    ret = {}
    for config_path in configs:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        seed_path = config["seed_custom_resource"]

        with open(seed_path, "r", encoding="utf-8") as f:
            seed = yaml.safe_load(f)
        key = seed["apiVersion"]

        context_path = os.path.join(
            os.path.dirname(os.path.abspath(config_path)), "context.json"
        )
        with open(context_path, "r", encoding="utf-8") as f:
            context = json.load(f)

        input_model = DeterministicInputModel(
            crd=context["crd"]["body"],
            seed_input=defaultdict(lambda: defaultdict(dict)),
            used_fields=[],
            example_dir=None,
            num_workers=1,
            num_cases=1,
        )
        ret[key] = (context, input_model)
    return ret


mapping = input_model_and_context_mapping()


def checker_func(s: Snapshot, prev_s: Snapshot) -> Optional[OracleResult]:
    api_version = s.input_cr["apiVersion"]
    checker = ConsistencyChecker(
        trial_dir="",
        input_model=mapping[api_version][1],
        context=mapping[api_version][0],
    )
    checker.write_delta_log = lambda *args: None  # type: ignore
    return checker.check(0, s, prev_s)


@pytest.mark.parametrize(
    "test_case_id,result_dict",
    list(
        enumerate(
            [
                ConsistencyOracleResult(
                    message="Found no matching fields for input",
                    input_diff=Diff(
                        prev=NotPresent(),
                        curr="ACTOKEY",
                        path=PropertyPath(
                            [
                                "spec",
                                "additionalServiceConfig",
                                "nodePortService",
                                "additionalAnnotations",
                                "ACTOKEY",
                            ]
                        ),
                    ),
                ),
                None,
                InvalidInputResult(
                    message="Invalid input determined from status message: "
                    'StatefulSet.apps "test-cluster-server" is invalid: '
                    "spec.template.spec.restartPolicy: Unsupported value: "
                    '"OnFailure": supported values: "Always"',
                    responsible_property=PropertyPath([]),
                ),
                None,
                None,
                None,
                None,
                None,
                None,
            ]
        )
    ),
)
def test_consistency_checker(test_case_id, result_dict):
    snapshot = load_snapshot("state", test_case_id)
    snapshot_prev = load_snapshot("state", test_case_id, load_prev=True)
    oracle_result = checker_func(snapshot, snapshot_prev)
    assert oracle_result == result_dict
