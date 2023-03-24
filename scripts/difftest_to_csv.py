import argparse
import glob
import json
import os
import re
import pandas as pd

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Script to convert feature results to xlsx')
    parser.add_argument('--testrun-dir', help='Directory to check', required=True)
    args = parser.parse_args()

    compare_results = glob.glob(os.path.join(args.testrun_dir, 'compare-results-*.json'))

    df = pd.DataFrame(columns=['digest', 'delta', 'trial', 'gen'])
    for compare_result in compare_results:
        digest = re.search('compare-results-(.*).json', compare_result).group(1)
        with open(compare_result, 'r') as f:
            errors = json.load(f)

        rows = []
        for error in errors:
            rows.append({'digest': digest, 'delta': error['delta'], 'trial': error['trial'], 'gen': error['gen']})

        df = pd.concat([df, pd.DataFrame(rows)])

    df.to_csv(os.path.join(args.testrun_dir, 'result.csv'), index=False)