"""Integration tests for cass-operator bugs."""

import json
import os
import pathlib
import unittest

import yaml

from acto import acto_config
from acto.checker.checker_set import CheckerSet
from acto.input.input import DeterministicInputModel, InputModel
from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_diff_test import DiffTestResult, PostDiffTest
from acto.snapshot import Snapshot
from acto.trial import Step

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestCassOpBugs(unittest.TestCase):
    """Integration tests for cass-operator bugs."""

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        # prepare and load config
        config_path = os.path.join(
            test_dir.parent.parent,
            "data",
            "cass-operator",
            "v1-10-3",
            "config.json",
        )
        with open(config_path, "r", encoding="utf-8") as config_file:
            self.config = OperatorConfig.model_validate(json.load(config_file))

        # prepare context
        context_file = os.path.join(
            os.path.dirname(self.config.seed_custom_resource), "context.json"
        )
        with open(context_file, "r", encoding="utf-8") as context_fin:
            self.context = json.load(context_fin)
            self.context["preload_images"] = set(self.context["preload_images"])

        # prepare feature gate
        acto_config.load_config()

        # prepare input model
        with open(
            self.config.seed_custom_resource, "r", encoding="utf-8"
        ) as cr_file:
            self.seed = yaml.load(cr_file, Loader=yaml.FullLoader)
        self.input_model: InputModel = DeterministicInputModel(
            crd=self.context["crd"]["body"],
            seed_input=self.seed,
            example_dir=self.config.example_dir,
            num_workers=1,
            num_cases=1,
        )

    def test_cassop_330(self):
        """Test cassop-330."""
        # https://github.com/k8ssandra/cass-operator/issues/330

        trial_dir = os.path.join(test_data_dir, "cassop-330", "trial-00-0000")
        checker = CheckerSet(self.context, trial_dir, self.input_model, [])

        snapshot_0 = Snapshot.load(trial_dir, 1)
        snapshot_1 = Snapshot.load(trial_dir, 2)

        run_result = checker.check(snapshot_1, snapshot_0, 2)
        self.assertTrue(run_result.is_error())

    def test_cassop_330_diff(self):
        """Test cassop-330 diff test."""
        diff_test_result_path = os.path.join(
            test_data_dir,
            "cassop-330",
            "post_diff_test",
            "trial-00",
            "difftest-001.json",
        )
        diff_test_result = DiffTestResult.from_file(diff_test_result_path)

        trial_dir = os.path.join(test_data_dir, "cassop-330", "trial-00-0000")
        step = Step.load(trial_dir, 2)

        result = PostDiffTest.check_diff_test_step(
            diff_test_result, step, self.config
        )
        self.assertTrue(result is not None)

    def test_cassop_928(self):
        """Test cassop-928."""
        diff_test_result_path = os.path.join(
            test_data_dir,
            "cassop-315",
            "post_diff_test",
            "trial-00",
            "difftest-000.json",
        )
        diff_test_result = DiffTestResult.from_file(diff_test_result_path)
        trial_dir = os.path.join(test_data_dir, "cassop-315", "trial-00-0000")
        step = Step.load(trial_dir, 2)

        result = PostDiffTest.check_diff_test_step(
            diff_test_result, step, self.config
        )
        self.assertTrue(result is not None)


if __name__ == "__main__":
    unittest.main()
