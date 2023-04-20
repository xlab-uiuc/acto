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

if __name__ == '__main__':
    file_name = sys.argv[1]
    df = pd.read_excel(file_name, sheet_name='Dependency')
    df.set_index('Trial number', inplace=True)
    print(df)
    k8s_misconfigrows = df.loc[df['True/False'] == 'misconfiguration']
    print(k8s_misconfigrows)

    k8s_misconfigs = k8s_misconfigrows['testcase'].apply(lambda x: extract_field_from_testcase(x))

    print(k8s_misconfigs.unique().size)