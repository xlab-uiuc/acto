import json
import re
import pandas as pd
import sys

def extract_field_from_testcase(testcase):
    regex = r"'field':\s*'(\[.*?\])'"
    groups = re.search(regex, testcase)
    if groups:
        return groups.group(1)
    else:
        return None
    
def extract_trial_number(trial_number):
    trial_number = trial_number.split('-')[0] + '-' + trial_number.split('-')[1]
    return trial_number

if __name__ == '__main__':
    file_name = sys.argv[1]
    df = pd.read_excel(file_name, sheet_name='Dependency')
    # df.set_index('Trial number', inplace=True)
    print(df)
    k8s_misconfigrows = df.loc[df['True/False'] == 'misconfiguration']
    recovery_alarms = df.loc[df['dependency_recovery_result'] != 'Pass']
    print(k8s_misconfigrows)

    k8s_misconfigs = k8s_misconfigrows['testcase'].apply(lambda x: extract_field_from_testcase(x))

    misconfig_with_trial_nums = k8s_misconfigrows.copy()
    misconfig_with_trial_nums['Trial number'] = k8s_misconfigrows['Trial number'].apply(lambda x: extract_trial_number(x))

    misconfig_with_trial_nums = pd.merge(misconfig_with_trial_nums, recovery_alarms, on='Trial number', how='inner')
    misconfig_with_trial_nums = misconfig_with_trial_nums['testcase_x'].apply(lambda x: extract_field_from_testcase(x))
    print(misconfig_with_trial_nums)

    print(k8s_misconfigs.unique().size)
    print(misconfig_with_trial_nums.unique().size)