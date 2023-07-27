import argparse
import glob
import json
import os

import pandas

parser = argparse.ArgumentParser()
parser.add_argument('--repro-result', type=str, required=True)
args = parser.parse_args()

bug_testruns = glob.glob(f'{args.repro_result}/testrun-*')

bug_running_time = {}

for bug_testrun in bug_testruns:
    bug_id = bug_testrun.split('testrun-')[1]
    bug_running_time[bug_id] = {
        'k8s_bootstrap': 0,
        'operator_deploy': 0,
        'trial_run': 0,
        'total': 0,
    }
    trials = glob.glob(f'{bug_testrun}/trial-*')
    for trial in trials:
        result_path = os.path.join(trial, 'result.json')
        with open(result_path) as f:
            result = json.load(f)
            time_breakdown = result['time_breakdown']
            k8s_bootstrap = time_breakdown['k8s_bootstrap']
            operator_deploy = time_breakdown['operator_deploy']
            trial_run = time_breakdown['trial_run']

            bug_running_time[bug_id]['k8s_bootstrap'] += k8s_bootstrap
            bug_running_time[bug_id]['operator_deploy'] += operator_deploy
            bug_running_time[bug_id]['trial_run'] += trial_run
            bug_running_time[bug_id]['total'] += k8s_bootstrap + operator_deploy + trial_run

    if os.path.exists(f'{bug_testrun}/post_diff_test'):
        post_diff_trials = glob.glob(f'{bug_testrun}/post_diff_test/trial-*')
        for post_diff_trial in post_diff_trials:
            difftests = glob.glob(f'{post_diff_trial}/difftest-*')
            for difftest in difftests:
                with open(difftest, 'r') as difftest_f:
                    difftest_result = json.load(difftest_f)
                    time_breakdown = difftest_result['time']
                    k8s_bootstrap = time_breakdown['k8s_bootstrap']
                    operator_deploy = time_breakdown['operator_deploy']
                    trial_run = time_breakdown['run']

                    bug_running_time[bug_id]['k8s_bootstrap'] += k8s_bootstrap
                    bug_running_time[bug_id]['operator_deploy'] += operator_deploy
                    bug_running_time[bug_id]['trial_run'] += trial_run
                    bug_running_time[bug_id]['total'] += k8s_bootstrap + operator_deploy + trial_run

bug_running_time_df = pandas.DataFrame.from_dict(bug_running_time, orient='index')
print(bug_running_time_df)
print(f"Total time: {bug_running_time_df['total'].sum() / 60}, "
      f"average: {bug_running_time_df['total'].mean() / 60}, "
      f"min: {bug_running_time_df['total'].min() / 60}, "
      f"max: {bug_running_time_df['total'].max() / 60}")
print(f"Total bootstrap time: {bug_running_time_df['k8s_bootstrap'].sum() / 60}, "
      f"average: {bug_running_time_df['k8s_bootstrap'].mean() / 60}, "
      f"min: {bug_running_time_df['k8s_bootstrap'].min() / 60}, "
      f"max: {bug_running_time_df['k8s_bootstrap'].max() / 60}")
print(f"Total operator deploy time: {bug_running_time_df['operator_deploy'].sum() / 60}, "
      f"average: {bug_running_time_df['operator_deploy'].mean() / 60}, "
      f"min: {bug_running_time_df['operator_deploy'].min() / 60}, "
      f"max: {bug_running_time_df['operator_deploy'].max() / 60}")
print(
    f"Total trial run time: {bug_running_time_df['trial_run'].sum() / 60}",
    f"average: {bug_running_time_df['trial_run'].mean() / 60}, "
    f"min: {bug_running_time_df['trial_run'].min() / 60}, "
    f"max: {bug_running_time_df['trial_run'].max() / 60}")

bug_running_time_df['k8s_bootstrap']

with open('bug_running_time.json', 'w') as f:
    json.dump(bug_running_time, f, indent=4)