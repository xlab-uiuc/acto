import json
import os
import pathlib
import unittest

import yaml

from acto import config as acto_config
from acto.checker.checker_set import CheckerSet
from acto.input import DeterministicInputModel, InputModel
from acto.lib.operator_config import OperatorConfig

from .utils import construct_snapshot

test_dir = pathlib.Path(__file__).parent.resolve()


class TestCRDBOpBugs(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        # prepare and load config
        config_path = os.path.join(test_dir.parent, 'data', 'cockroach-operator', 'config.json')
        with open(config_path, 'r') as config_file:
            self.config = OperatorConfig(**json.load(config_file))

        # prepare context
        context_file = os.path.join(os.path.dirname(self.config.seed_custom_resource),
                                    'context.json')
        with open(context_file, 'r') as context_fin:
            self.context = json.load(context_fin)
            self.context['preload_images'] = set(self.context['preload_images'])

        # prepare feature gate
        acto_config.load_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crdb_bugs_config.yaml'))

        # prepare input model
        with open(self.config.seed_custom_resource, 'r') as cr_file:
            self.seed = yaml.load(cr_file, Loader=yaml.FullLoader)
        self.input_model: InputModel = DeterministicInputModel(
            self.context['crd']['body'], self.context['analysis_result']['used_fields'],
            self.config.example_dir, 1, 1, None)
        self.input_model.initialize(self.seed)

    def test_crdbop_920(self):
        # https://github.com/cockroachdb/cockroach-operator/issues/920

        trial_dir = os.path.join(test_dir, 'crdbop-920')
        checker = CheckerSet(self.context,
                          trial_dir,
                          self.input_model, [])

        snapshot_0 = construct_snapshot(trial_dir, 1)
        snapshot_1 = construct_snapshot(trial_dir, 2)

        runResult = checker.check(snapshot_1, snapshot_0, False, 2, {})
        self.assertTrue(runResult.is_error())


if __name__ == '__main__':
    unittest.main()