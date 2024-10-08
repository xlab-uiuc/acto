import json
import os
import pathlib
import unittest
from datetime import datetime

from acto.engine import Acto, apply_testcase
from acto.input.input import DeterministicInputModel
from acto.lib.operator_config import OperatorConfig

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestLearnPhase(unittest.TestCase):
    """Integration tests for Acto's learning phase."""

    def test_statefulset_operator(self):
        """Test statefulset operator."""
        workdir_path = f"testrun-{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
        os.makedirs(workdir_path, exist_ok=True)

        config_path = os.path.join(
            test_data_dir, "elastic-on-k8s", "config.json"
        )
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
            if "monkey_patch" in config:
                del config["monkey_patch"]
            config = OperatorConfig.model_validate(config)

        context_cache = os.path.join(
            os.path.dirname(config.seed_custom_resource), "context.json"
        )

        Acto(
            workdir_path=workdir_path,
            operator_config=config,
            cluster_runtime="KIND",
            context_file=context_cache,
            helper_crd=None,
            num_workers=1,
            num_cases=1,
            dryrun=False,
            analysis_only=False,
            is_reproduce=False,
            input_model=DeterministicInputModel,
            apply_testcase_f=apply_testcase,
            focus_fields=config.focus_fields,
        )
