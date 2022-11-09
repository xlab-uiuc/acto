import csv
import glob
import json
import sys
import os
import pandas as pd
import re

if __name__ == '__main__':
    result_folder = sys.argv[1]
    baseline_results = glob.glob(os.path.join(result_folder, '*', 'post-result-*-baseline.json'))
    canonicalization_results = glob.glob(
        os.path.join(result_folder, '*', 'post-result-*-canonicalization.json'))
    dependency_results = glob.glob(
        os.path.join(result_folder, '*', 'post-result-*-dependency_analysis.json'))
    taint_analysis_results = glob.glob(
        os.path.join(result_folder, '*', 'post-result-*-taint_analysis.json'))

    baseline_df = pd.DataFrame()
    canonicalization_df = pd.DataFrame()
    dependency_df = pd.DataFrame()
    taint_analysis_df = pd.DataFrame()

    for json_path in baseline_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            baseline_df = baseline_df.append(
                {
                    'Trial number': json_instance['post_result']['trial_num'],
                    'baseline_alarm': json_instance['alarm'],
                    'baseline_crash_result': json_instance['post_result']['error']['crash_result'],
                    'baseline_recovery_result': json_instance['post_result']['error']['recovery_result'],
                    'baseline_state_result': json_instance['post_result']['error']['state_result'],
                    'baseline_custom_result': json_instance['post_result']['error']['custom_result']
                },
                ignore_index=True)

    for json_path in canonicalization_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            canonicalization_df = canonicalization_df.append(
                {
                    'Trial number': json_instance['post_result']['trial_num'],
                    'canonicalization_alarm': json_instance['alarm'],
                    'canonicalization_crash_result': json_instance['post_result']['error']['crash_result'],
                    'canonicalization_recovery_result': json_instance['post_result']['error']['recovery_result'],
                    'canonicalization_state_result': json_instance['post_result']['error']['state_result'],
                    'canonicalization_custom_result': json_instance['post_result']['error']['custom_result']
                },
                ignore_index=True)

    for json_path in dependency_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            dependency_df = dependency_df.append(
                {
                    'Trial number': json_instance['post_result']['trial_num'],
                    'dependency_alarm': json_instance['alarm'],
                    'dependency_crash_result': json_instance['post_result']['error']['crash_result'],
                    'dependency_recovery_result': json_instance['post_result']['error']['recovery_result'],
                    'dependency_state_result': json_instance['post_result']['error']['state_result'],
                    'dependency_custom_result': json_instance['post_result']['error']['custom_result']
                },
                ignore_index=True)

    for json_path in taint_analysis_results:
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            taint_analysis_df = taint_analysis_df.append(
                {
                    'Trial number': json_instance['post_result']['trial_num'],
                    'taint_analysis_alarm': json_instance['alarm'],
                    'taint_analysis_crash_result': json_instance['post_result']['error']['crash_result'],
                    'taint_analysis_recovery_result': json_instance['post_result']['error']['recovery_result'],
                    'taint_analysis_state_result': json_instance['post_result']['error']['state_result'],
                    'taint_analysis_custom_result': json_instance['post_result']['error']['custom_result']
                },
                ignore_index=True)

    merged = pd.merge(baseline_df, canonicalization_df, on='Trial number')
    merged = pd.merge(merged, taint_analysis_df, on='Trial number')
    merged = pd.merge(merged, dependency_df, on='Trial number')
    merged= merged.drop(columns=list(merged.filter(regex = '_result')))
    merged = merged.sort_values(by=['Trial number'])

    merged.to_csv(os.path.join(result_folder, 'merged.csv'), index=False)
    baseline_df.to_csv(os.path.join(result_folder, 'baseline.csv'), index=False)
    canonicalization_df.to_csv(os.path.join(result_folder, 'canonicalization.csv'), index=False)
    dependency_df.to_csv(os.path.join(result_folder, 'dependency.csv'), index=False)
    taint_analysis_df.to_csv(os.path.join(result_folder, 'taint_analysis.csv'), index=False)

    print(merged['baseline_alarm'].value_counts())
    print(merged['canonicalization_alarm'].value_counts())
    print(merged['taint_analysis_alarm'].value_counts())
    print(merged['dependency_alarm'].value_counts())