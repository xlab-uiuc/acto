'''
Commented out because it is not used in the project.
TODO: refactor to fix the dependency issue

import json
import sys
import unittest

import yaml

from acto.checker import Checker
from acto.common import InvalidInputResult
from acto.snapshot import Snapshot


class TestChecker(unittest.TestCase):

    def test_invalid_input_message(self):
        checker = Checker({'namespace': ''}, '')

        mutated_0_path = 'mutated-0.yaml'
        mutated_1_path = 'mutated-1.yaml'
        operator_log_0_path = 'operator-0.log'
        operator_log_1_path = 'operator-1.log'
        system_state_0_path = 'system-state-000.json'
        system_state_1_path = 'system-state-001.json'
        cli_output_0_path = 'cli-output-0.log'
        cli_output_1_path = 'cli-output-1.log'

        with open(mutated_0_path, 'r') as mutated_0_file, \
                open(mutated_1_path, 'r') as mutated_1_file, \
                open(operator_log_0_path, 'r') as operator_log_0_file, \
                open(operator_log_1_path, 'r') as operator_log_1_file, \
                open(system_state_0_path, 'r') as system_state_0_file, \
                open(system_state_1_path, 'r') as system_state_1_file, \
                open(cli_output_0_path, 'r') as cli_output_0_file, \
                open(cli_output_1_path, 'r') as cli_output_1_file:

            mutated_0 = yaml.load(mutated_0_file, Loader=yaml.FullLoader)
            mutated_1 = yaml.load(mutated_1_file, Loader=yaml.FullLoader)
            operator_log_0 = operator_log_0_file.read().splitlines()
            operator_log_1 = operator_log_1_file.read().splitlines()
            system_state_0 = json.load(system_state_0_file)
            system_state_1 = json.load(system_state_1_file)
            cli_output_0 = json.load(cli_output_0_file)
            cli_output_1 = json.load(cli_output_1_file)

            prev_snapshot = Snapshot(mutated_0, cli_output_0, system_state_0, operator_log_0)
            curr_snapshot = Snapshot(mutated_1, cli_output_1, system_state_1, operator_log_1)

            self.assertTrue(
                isinstance(checker.check_operator_log(curr_snapshot, prev_snapshot),
                           InvalidInputResult))


if __name__ == '__main__':
    unittest.main()

'''