"""Integration tests for the rabbitmq-operator bugs."""

import json
import os
import pathlib
import unittest

import yaml

from acto import acto_config
from acto.checker.checker_set import CheckerSet
from acto.input.input import DeterministicInputModel, InputModel
from acto.lib.operator_config import OperatorConfig
from acto.snapshot import Snapshot

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestRabbitMQOpBugs(unittest.TestCase):
    """Integration tests for the rabbitmq-operator bugs."""

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        # prepare and load config
        config_path = os.path.join(
            test_dir.parent.parent, "data", "rabbitmq-operator", "config.json"
        )
        with open(config_path, "r", encoding="utf-8") as config_file:
            self.config = OperatorConfig(**json.load(config_file))

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
            custom_module_path=self.config.custom_module,
        )

    def test_rbop_928(self):
        """Test rabbitmq-operator rabbitmq-operator-928."""
        # https://github.com/rabbitmq/cluster-operator/issues/928

        trial_dir = os.path.join(test_data_dir, "rbop-928")
        checker = CheckerSet(self.context, trial_dir, self.input_model, [])

        snapshot_0 = Snapshot.load(trial_dir, 1)
        snapshot_1 = Snapshot.load(trial_dir, 2)

        run_result = checker.check(snapshot_1, snapshot_0, 2)
        self.assertTrue(run_result.is_error())


if __name__ == "__main__":
    unittest.main()
