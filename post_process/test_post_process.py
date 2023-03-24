import unittest
import sys
import yaml
import json

from common import OperatorConfig
from .post_process import PostProcessor
from .post_diff_test import PostDiffTest

class TestPostProcessor(unittest.TestCase):

    def test_construction(self):

        with open('/home/tyler/acto/data/cass-operator/config.json', 'r') as config_file:
            config = OperatorConfig(**json.load(config_file))
        p = PostProcessor(testrun_dir='/home/tyler/acto-data/cass-operator/testrun-cass-whitebox-1',
                          config=config)
        
class TestPostDiffTest(unittest.TestCase):

    def test_construction(self):

        with open('/home/tyler/acto/data/cass-operator/config.json', 'r') as config_file:
            config = OperatorConfig(**json.load(config_file))
        p = PostDiffTest(testrun_dir='/home/tyler/acto-data/cass-operator/testrun-cass-whitebox-1',
                          config=config)
        
    def test_comparison(self):
        with open('/home/tyler/acto/data/cass-operator/config.json', 'r') as config_file:
            config = OperatorConfig(**json.load(config_file))
        p = PostDiffTest(testrun_dir='/home/tyler/acto-data/cass-operator/testrun-cass-whitebox-1',
                          config=config)
        with open('/home/tyler/acto/testrun-cass-whitebox-1/difftest/trial-00/difftest-003.json', 'r') as f, \
            open('compare_results.json', 'w') as result_f:
            diff_test_result = json.load(f)
            error = p.check_diff_test_result(diff_test_result)
            if error:
                result_f.write(json.dumps(error.to_dict(), indent=6))

if __name__ == '__main__':
    unittest.main()