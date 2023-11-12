import argparse
import glob
import json
import os
import sys

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Script to convert feature results to xlsx')
    parser.add_argument('--testrun-dir', help='Directory to check', required=True)
    args = parser.parse_args()

    result_folder = args.testrun_dir

    baseline_results = glob.glob(os.path.join(
        result_folder, 'trial-??-????', 'generation-*-runtime.json'))
    recovery_results = glob.glob(os.path.join(result_folder, 'trial-??-????', 'result.json'))
    difftest_results = glob.glob(os.path.join(
        result_folder, 'post_diff_test', 'compare-results-*.json'))
    difftest_mutated_files = glob.glob(os.path.join(
        result_folder, 'post_diff_test', 'trial-??', 'mutated-*.yaml'))
    recovery_files = glob.glob(os.path.join(result_folder, 'trial-??-????', 'mutated--1.yaml'))

    baseline_df = pd.DataFrame()

    baseline_df_list = []

    testcase_set = set()
    print(f"Found {len(baseline_results)} baseline results")
    for json_path in baseline_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            post_result = json_instance
            if post_result['crash_result'] == None:
                crash_result = 'Pass'
            elif isinstance(post_result['crash_result'], dict):
                crash_result = post_result['crash_result']['message']
            elif post_result['crash_result'] == 'Pass':
                crash_result = 'Pass'

            if post_result['health_result'] == None:
                health_result = 'Pass'
            elif isinstance(post_result['health_result'], dict):
                health_result = post_result['health_result']['message']
            elif post_result['health_result'] == 'Pass':
                health_result = 'Pass'

            if post_result['state_result'] == None:
                post_state_result = 'Pass'
            elif isinstance(post_result['state_result'], dict):
                post_state_result = post_result['state_result']['input_delta']['path']
            elif post_result['state_result'] == 'Pass':
                post_state_result = 'Pass'

            if post_result['recovery_result'] == None:
                recovery_result = 'Pass'
            elif isinstance(post_result['recovery_result'], dict):
                recovery_result = post_result['recovery_result']['delta']
            elif post_result['recovery_result'] == 'Pass':
                recovery_result = 'Pass'

            if post_result['custom_result'] == None:
                custom_result = 'Pass'
            elif isinstance(post_result['custom_result'], dict):
                custom_result = post_result['custom_result']['message']
            elif post_result['custom_result'] == 'Pass':
                custom_result = 'Pass'

            if json_instance['testcase'] != None:
                field = json_instance['testcase']['field']
                testcase = json_instance['testcase']['testcase']
                testcase_set.add(f"{field}-{testcase}")

                trial_num = os.path.basename(os.path.dirname(json_path))
                alarm = crash_result != 'Pass' or recovery_result != 'Pass' or post_state_result != 'Pass' or custom_result != 'Pass' or health_result != 'Pass'
                baseline_df_list.append({
                    'Trial number': trial_num,
                    'testcase': json_instance['testcase'],
                    'baseline_alarm': alarm,
                    'baseline_crash_result': crash_result,
                    'baseline_health_result': health_result,
                    'baseline_recovery_result': recovery_result,
                    'baseline_state_result': post_state_result,
                    'baseline_custom_result': custom_result
                })

    print(f"Found {len(recovery_files)} recovery results")
    for json_path in recovery_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            if 'error' in json_instance:
                if json_instance['error']['recovery_result'] == None:
                    recovery_result = 'Pass'
                elif json_instance['error']['recovery_result'] == 'Pass':
                    recovery_result = 'Pass'
                elif isinstance(json_instance['error']['recovery_result'], dict):
                    recovery_result = json_instance['error']['recovery_result']['delta']
            else:
                recovery_result = 'Pass'

            recovery_alarm = recovery_result != 'Pass'

            trial_num = os.path.basename(os.path.dirname(json_path))
            baseline_df_list.append({
                'Trial number': trial_num,
                'baseline_alarm': recovery_alarm,
                'baseline_crash_result': 'Pass',
                'baseline_health_result': 'Pass',
                'baseline_recovery_result': recovery_result,
                'baseline_state_result': 'Pass',
                'baseline_custom_result': 'Pass'
            })

    print(f"Found {len(difftest_mutated_files)} difftest results")
    for json_path in difftest_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)
            for alarm in json_instance:
                baseline_df_list.append({
                    'Trial number': f"{os.path.basename(json_path)}",
                    'baseline_alarm': True,
                    'baseline_crash_result': 'Pass',
                    'baseline_health_result': 'Pass',
                    'baseline_recovery_result': alarm["delta"],
                    'baseline_state_result': 'Pass',
                    'baseline_custom_result': 'Pass'
                })
                break  # only one alarm per file

    baseline_df = pd.DataFrame(baseline_df_list)

    baseline_df = baseline_df.sort_values(by=['Trial number'])

    with open(os.path.join(result_folder, 'result.csv'), mode='w') as writer:
        baseline_df.to_csv(writer, index=False)
