import json
import os
import pathlib
import unittest

from acto.utils import OperatorConfig

from .post_diff_test import PostDiffTest
from .post_process import PostProcessor

test_dir = pathlib.Path(__file__).parent.resolve()

class TestPostProcessor(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        config_path = os.path.join(test_dir.parent.parent, 'data', 'cass-operator', 'config.json')
        self.testrun_dir = os.path.join(test_dir, 'test_data', 'testrun-cass-whitebox-1')

        with open(config_path, 'r') as config_file:
            self.config = OperatorConfig(**json.load(config_file))

    def test_construction(self):
        p = PostProcessor(testrun_dir=self.testrun_dir,
                          config=self.config)
        
class TestPostDiffTest(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        config_path = os.path.join(test_dir.parent.parent, 'data', 'cass-operator', 'config.json')
        self.testrun_dir = os.path.join(test_dir, 'test_data', 'testrun-cass-whitebox-1')

        with open(config_path, 'r') as config_file:
            self.config = OperatorConfig(**json.load(config_file))

    def test_construction(self):
        p = PostDiffTest(testrun_dir=self.testrun_dir,
                          config=self.config)
        
    # FIXME
    # def test_comparison(self):
    #     p = PostDiffTest(testrun_dir=self.testrun_dir,
    #                       config=self.config)
    #     os.path.join(self.testrun_dir, 'difftest', 'trial-00', 'difftest-003.json')
    #     with open(os.path.join(self.testrun_dir, 'difftest', 'trial-00', 'difftest-003.json'), 'r') as f, \
    #         open('compare_results.json', 'w') as result_f:
    #         diff_test_result = json.load(f)
    #         error = p.check_diff_test_result(diff_test_result)
    #         if error:
    #             result_f.write(json.dumps(error.to_dict(), indent=6))

if __name__ == '__main__':
    unittest.main()