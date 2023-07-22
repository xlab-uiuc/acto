import json
import os
import pathlib
import unittest

import yaml

from acto import config as acto_config
from acto.checker.checker import OracleControlFlow
from acto.checker.checker_set import CheckerSet
from acto.input import DeterministicInputModel, InputModel
from acto.post_process.post_diff_test import PostDiffTest
from acto.utils import OperatorConfig
from test.post_diff_test_helper import FileBasedTrial, DiffTestResultTrial

from .utils import construct_snapshot

test_dir = pathlib.Path(__file__).parent.resolve()


class TestCassOpBugs(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        # prepare and load config
        config_path = os.path.join(test_dir.parent, 'data', 'cass-operator', 'config.json')
        with open(config_path, 'r') as config_file:
            self.config = OperatorConfig(**json.load(config_file))

        # prepare context
        context_file = os.path.join(os.path.dirname(self.config.seed_custom_resource),
                                    'context.json')
        with open(context_file, 'r') as context_fin:
            self.context = json.load(context_fin)
            self.context['preload_images'] = set(self.context['preload_images'])

        # prepare feature gate
        acto_config.load_config(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cassop_bugs_config.yaml'))

        # prepare input model
        with open(self.config.seed_custom_resource, 'r') as cr_file:
            self.seed = yaml.load(cr_file, Loader=yaml.FullLoader)
        self.input_model: InputModel = DeterministicInputModel(
            self.context['crd']['body'], self.context['analysis_result']['used_fields'],
            self.config.example_dir, 1, 1, None)
        self.input_model.initialize(self.seed)

    def test_cassop_330(self):
        # https://github.com/k8ssandra/cass-operator/issues/330

        trial_dir = os.path.join(test_dir, 'cassop-330')
        checker = CheckerSet(self.context,
                             self.input_model)

        snapshot_0 = construct_snapshot(trial_dir, 1)
        snapshot_1 = construct_snapshot(trial_dir, 2)

        runResult = checker.check(snapshot_1, snapshot_0)
        self.assertFalse(all(map(lambda test: test.means(OracleControlFlow.ok), runResult)))

    def test_cassop_330_diff(self):
        diff_test_result_path = os.path.join(test_dir, 'cassop-330', 'difftest-006.json')
        with open(diff_test_result_path, 'r') as f:
            diff_test_result = json.load(f)

        diff_test = PostDiffTest({
            'trial-00-0001': FileBasedTrial(os.path.join(test_dir, 'cassop-330', 'trial-00-0001'))
        }, self.config, num_workers=0)

        result = diff_test.check_for_a_trial(DiffTestResultTrial(diff_test_result))
        self.assertEquals(result[0]['diff_test']['message'],
                          "failed attempt recovering to seed state - system state diff: "
                          "{'dictionary_item_removed': [<root['service']['cluster1-seed-service']['metadata']['labels']['ACTOKEY'] "
                          "t1:'ACTOKEY', t2:not present>]}")

    def test_cassop_928(self):
        diff_test_result_path = os.path.join(test_dir, 'cassop-315', 'difftest-002.json')
        with open(diff_test_result_path, 'r') as f:
            diff_test_result = json.load(f)

        diff_test = PostDiffTest({
            'trial-04-0000': FileBasedTrial(os.path.join(test_dir, 'cassop-315', 'trial-04-0000'))
        }, self.config, num_workers=0)

        result = diff_test.check_for_a_trial(DiffTestResultTrial(diff_test_result))
        self.assertEquals(result[0]['diff_test']['message'],
                          "failed attempt recovering to seed state - system state diff: "
                          "{'dictionary_item_removed': [<root['pod_disruption_budget']['test-cluster-pdb'] "
                          "t1:{'api_versio...}, t2:not present>]}")


if __name__ == '__main__':
    unittest.main()
