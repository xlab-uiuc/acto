import argparse
import csv
import glob
import json
import sys
import os
import pandas as pd
import re

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Script to convert feature results to xlsx')
    parser.add_argument('--testrun-dir', help='Directory to check', required=True)
    parser.add_argument('--testplan', help='Testplan', required=False)
    parser.add_argument('--previous', help='Previous result', type=str)
    args = parser.parse_args()

    result_folder = args.testrun_dir
    if args.testplan:
        test_plan_path = args.testplan
    else:
        test_plan_path = os.path.join(result_folder, 'test_plan.json')

    if args.previous:
        previous_inspection = args.previous

        with open(previous_inspection, 'rb') as f:
            previous_df = pd.read_excel(f, sheet_name='Overview', index_col=0, usecols=['Trial number', 'testcase_x', 'True/False'])

    baseline_results = glob.glob(os.path.join(result_folder, '*', 'post-result-*-baseline.json'))
    canonicalization_results = glob.glob(
        os.path.join(result_folder, '*', 'post-result-*-canonicalization.json'))
    dependency_results = glob.glob(
        os.path.join(result_folder, '*', 'post-result-*-dependency_analysis.json'))
    taint_analysis_results = glob.glob(
        os.path.join(result_folder, '*', 'post-result-*-taint_analysis.json'))
    recovery_results = glob.glob(os.path.join(result_folder, '*', 'result.json'))

    with open(test_plan_path, 'r') as f:
        test_plan = json.load(f)

        normal_testplan = test_plan['planned_normal_testcases']
        semantic_testplan = test_plan['semantic_testcases']

    baseline_df = pd.DataFrame()
    canonicalization_df = pd.DataFrame()
    dependency_df = pd.DataFrame()
    taint_analysis_df = pd.DataFrame()

    for json_path in baseline_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            post_result = json_instance['post_result']
            if post_result['error']['crash_result'] == None:
                crash_result = 'Pass'
            elif isinstance(post_result['error']['crash_result'], dict):
                crash_result = post_result['error']['crash_result']['message']
            elif post_result['error']['crash_result'] == 'Pass':
                crash_result = 'Pass'

            if post_result['error']['health_result'] == None:
                health_result = 'Pass'
            elif isinstance(post_result['error']['health_result'], dict):
                health_result = post_result['error']['health_result']['message']
            elif post_result['error']['health_result'] == 'Pass':
                health_result = 'Pass'

            if post_result['error']['state_result'] == None:
                post_state_result = 'Pass'
            elif isinstance(post_result['error']['state_result'], dict):
                post_state_result = post_result['error']['state_result']['input_delta'][
                    'path']
            elif post_result['error']['state_result'] == 'Pass':
                post_state_result = 'Pass'

            if post_result['error']['recovery_result'] == None:
                recovery_result = 'Pass'
            elif isinstance(post_result['error']['recovery_result'], dict):
                recovery_result = post_result['error']['recovery_result']['delta']
            elif post_result['error']['recovery_result'] == 'Pass':
                recovery_result = 'Pass'

            if post_result['error']['custom_result'] == None:
                custom_result = 'Pass'
            elif isinstance(post_result['error']['custom_result'], dict):
                custom_result = post_result['error']['custom_result']['message']
            elif post_result['error']['custom_result'] == 'Pass':
                custom_result = 'Pass'

            if json_instance['post_result']['error']['testcase'] != None:
                field = json_instance['post_result']['error']['testcase']['field']
                testcase = json_instance['post_result']['error']['testcase']['testcase']

                if field in test_plan and testcase in test_plan[field] or field in semantic_testplan and testcase in semantic_testplan[field]:
                    baseline_df = baseline_df.append(
                        {
                            'Trial number': json_instance['post_result']['trial_num'],
                            'testcase': json_instance['post_result']['error']['testcase'],
                            'baseline_alarm': json_instance['alarm'],
                            'baseline_crash_result': crash_result,
                            'baseline_health_result': health_result,
                            'baseline_recovery_result': recovery_result,
                            'baseline_state_result': post_state_result,
                            'baseline_custom_result': custom_result
                        },
                        ignore_index=True)
                else:
                    print('Testcase {} is not in test plan'.format(json_instance['post_result']['error']['testcase']))

    for json_path in canonicalization_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            post_result = json_instance['post_result']
            if post_result['error']['crash_result'] == None:
                crash_result = 'Pass'
            elif isinstance(post_result['error']['crash_result'], dict):
                crash_result = post_result['error']['crash_result']['message']
            elif post_result['error']['crash_result'] == 'Pass':
                crash_result = 'Pass'

            if post_result['error']['health_result'] == None:
                health_result = 'Pass'
            elif isinstance(post_result['error']['health_result'], dict):
                health_result = post_result['error']['health_result']['message']
            elif post_result['error']['health_result'] == 'Pass':
                health_result = 'Pass'

            if post_result['error']['state_result'] == None:
                post_state_result = 'Pass'
            elif isinstance(post_result['error']['state_result'], dict):
                post_state_result = post_result['error']['state_result']['input_delta'][
                    'path']
            elif post_result['error']['state_result'] == 'Pass':
                post_state_result = 'Pass'

            if post_result['error']['recovery_result'] == None:
                recovery_result = 'Pass'
            elif isinstance(post_result['error']['recovery_result'], dict):
                recovery_result = post_result['error']['recovery_result']['delta']
            elif post_result['error']['recovery_result'] == 'Pass':
                recovery_result = 'Pass'

            if post_result['error']['custom_result'] == None:
                custom_result = 'Pass'
            elif isinstance(post_result['error']['custom_result'], dict):
                custom_result = post_result['error']['custom_result']['message']
            elif post_result['error']['custom_result'] == 'Pass':
                custom_result = 'Pass'

            if json_instance['post_result']['error']['testcase'] != None:
                field = json_instance['post_result']['error']['testcase']['field']
                testcase = json_instance['post_result']['error']['testcase']['testcase']

                if field in test_plan and testcase in test_plan[field] or field in semantic_testplan and testcase in semantic_testplan[field]:
                    canonicalization_df = canonicalization_df.append(
                        {
                            'Trial number': json_instance['post_result']['trial_num'],
                            'testcase': json_instance['post_result']['error']['testcase'],
                            'canonicalization_alarm': json_instance['alarm'],
                            'canonicalization_crash_result': crash_result,
                            'canonicalization_health_result': health_result,
                            'canonicalization_recovery_result': recovery_result,
                            'canonicalization_state_result': post_state_result,
                            'canonicalization_custom_result': custom_result
                        },
                        ignore_index=True)

    for json_path in dependency_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            post_result = json_instance['post_result']
            if post_result['error']['crash_result'] == None:
                crash_result = 'Pass'
            elif isinstance(post_result['error']['crash_result'], dict):
                crash_result = post_result['error']['crash_result']['message']
            elif post_result['error']['crash_result'] == 'Pass':
                crash_result = 'Pass'

            if post_result['error']['health_result'] == None:
                health_result = 'Pass'
            elif isinstance(post_result['error']['health_result'], dict):
                health_result = post_result['error']['health_result']['message']
            elif post_result['error']['health_result'] == 'Pass':
                health_result = 'Pass'

            if post_result['error']['state_result'] == None:
                post_state_result = 'Pass'
            elif isinstance(post_result['error']['state_result'], dict):
                post_state_result = post_result['error']['state_result']['input_delta'][
                    'path']
            elif post_result['error']['state_result'] == 'Pass':
                post_state_result = 'Pass'

            if post_result['error']['recovery_result'] == None:
                recovery_result = 'Pass'
            elif isinstance(post_result['error']['recovery_result'], dict):
                recovery_result = post_result['error']['recovery_result']['delta']
            elif post_result['error']['recovery_result'] == 'Pass':
                recovery_result = 'Pass'

            if post_result['error']['custom_result'] == None:
                custom_result = 'Pass'
            elif isinstance(post_result['error']['custom_result'], dict):
                custom_result = post_result['error']['custom_result']['message']
            elif post_result['error']['custom_result'] == 'Pass':
                custom_result = 'Pass'

            if json_instance['post_result']['error']['testcase'] != None:
                field = json_instance['post_result']['error']['testcase']['field']
                testcase = json_instance['post_result']['error']['testcase']['testcase']

                if field in test_plan and testcase in test_plan[field] or field in semantic_testplan and testcase in semantic_testplan[field]:

                    dependency_df = dependency_df.append(
                        {
                            'Trial number': json_instance['post_result']['trial_num'],
                            'testcase': json_instance['post_result']['error']['testcase'],
                            'dependency_alarm': json_instance['alarm'],
                            'dependency_crash_result': crash_result,
                            'dependency_health_result': health_result,
                            'dependency_recovery_result': recovery_result,
                            'dependency_state_result': post_state_result,
                            'dependency_custom_result': custom_result
                        },
                        ignore_index=True)

    for json_path in taint_analysis_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            post_result = json_instance['post_result']
            if post_result['error']['crash_result'] == None:
                crash_result = 'Pass'
            elif isinstance(post_result['error']['crash_result'], dict):
                crash_result = post_result['error']['crash_result']['message']
            elif post_result['error']['crash_result'] == 'Pass':
                crash_result = 'Pass'

            if post_result['error']['health_result'] == None:
                health_result = 'Pass'
            elif isinstance(post_result['error']['health_result'], dict):
                health_result = post_result['error']['health_result']['message']
            elif post_result['error']['health_result'] == 'Pass':
                health_result = 'Pass'

            if post_result['error']['state_result'] == None:
                post_state_result = 'Pass'
            elif isinstance(post_result['error']['state_result'], dict):
                post_state_result = post_result['error']['state_result']['input_delta'][
                    'path']
            elif post_result['error']['state_result'] == 'Pass':
                post_state_result = 'Pass'

            if post_result['error']['recovery_result'] == None:
                recovery_result = 'Pass'
            elif isinstance(post_result['error']['recovery_result'], dict):
                recovery_result = post_result['error']['recovery_result']['delta']
            elif post_result['error']['recovery_result'] == 'Pass':
                recovery_result = 'Pass'

            if post_result['error']['custom_result'] == None:
                custom_result = 'Pass'
            elif isinstance(post_result['error']['custom_result'], dict):
                custom_result = post_result['error']['custom_result']['message']
            elif post_result['error']['custom_result'] == 'Pass':
                custom_result = 'Pass'

            if json_instance['post_result']['error']['testcase'] != None:
                field = json_instance['post_result']['error']['testcase']['field']
                testcase = json_instance['post_result']['error']['testcase']['testcase']

                if field in test_plan and testcase in test_plan[field] or field in semantic_testplan and testcase in semantic_testplan[field]:
                    taint_analysis_df = taint_analysis_df.append(
                        {
                            'Trial number': json_instance['post_result']['trial_num'],
                            'testcase': json_instance['post_result']['error']['testcase'],
                            'taint_analysis_alarm': json_instance['alarm'],
                            'taint_analysis_crash_result': crash_result,
                            'taint_analysis_health_result': health_result,
                            'taint_analysis_recovery_result': recovery_result,
                            'taint_analysis_state_result': post_state_result,
                            'taint_analysis_custom_result': custom_result
                        },
                        ignore_index=True)

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

            baseline_df = baseline_df.append(
                {
                    'Trial number': json_instance['trial_num'],
                    'baseline_alarm': recovery_alarm,
                    'baseline_crash_result': 'Pass',
                    'baseline_health_result': 'Pass',
                    'baseline_recovery_result': recovery_result,
                    'baseline_state_result': 'Pass',
                    'baseline_custom_result': 'Pass'
                },
                ignore_index=True)

            canonicalization_df = canonicalization_df.append(
                {
                    'Trial number': json_instance['trial_num'],
                    'canonicalization_alarm': recovery_alarm,
                    'canonicalization_crash_result': 'Pass',
                    'canonicalization_health_result': 'Pass',
                    'canonicalization_recovery_result': recovery_result,
                    'canonicalization_state_result': 'Pass',
                    'canonicalization_custom_result': 'Pass'
                },
                ignore_index=True)

            taint_analysis_df = taint_analysis_df.append(
                {
                    'Trial number': json_instance['trial_num'],
                    'taint_analysis_alarm': recovery_alarm,
                    'taint_analysis_crash_result': 'Pass',
                    'taint_analysis_health_result': 'Pass',
                    'taint_analysis_recovery_result': recovery_result,
                    'taint_analysis_state_result': 'Pass',
                    'taint_analysis_custom_result': 'Pass'
                },
                ignore_index=True)

            dependency_df = dependency_df.append(
                {
                    'Trial number': json_instance['trial_num'],
                    'dependency_alarm': recovery_alarm,
                    'dependency_crash_result': 'Pass',
                    'dependency_health_result': 'Pass',
                    'dependency_recovery_result': recovery_result,
                    'dependency_state_result': 'Pass',
                    'dependency_custom_result': 'Pass'
                },
                ignore_index=True)

    merged = pd.merge(baseline_df, canonicalization_df, on='Trial number')
    merged = pd.merge(merged, taint_analysis_df, on='Trial number')
    merged = pd.merge(merged, dependency_df, on='Trial number')
    merged= merged.drop(columns=list(merged.filter(regex = '_result')))
    merged = merged.sort_values(by=['Trial number'])

    baseline_df = baseline_df.sort_values(by=['Trial number'])
    canonicalization_df = canonicalization_df.sort_values(by=['Trial number'])
    taint_analysis_df = taint_analysis_df.sort_values(by=['Trial number'])
    dependency_df = dependency_df.sort_values(by=['Trial number'])


    if args.previous:
        merged = pd.merge(merged, previous_df, on='Trial number', how='left')

    with pd.ExcelWriter(os.path.join(result_folder, 'result.xlsx'), mode='w') as writer:
        merged.to_excel(writer, sheet_name='Overview', index=False)
        baseline_df.to_excel(writer, sheet_name='Baseline', index=False)
        canonicalization_df.to_excel(writer, sheet_name='Canonicalization', index=False)
        taint_analysis_df.to_excel(writer, sheet_name='Taint analysis', index=False)
        dependency_df.to_excel(writer, sheet_name='Dependency', index=False)

    print(merged['baseline_alarm'].value_counts())
    print(merged['canonicalization_alarm'].value_counts())
    print(merged['taint_analysis_alarm'].value_counts())
    print(merged['dependency_alarm'].value_counts())