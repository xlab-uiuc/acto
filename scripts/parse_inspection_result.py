import pandas as pd
import sys

if __name__ == '__main__':
    file_name = sys.argv[1]
    df = pd.read_excel(file_name, sheet_name='Overview')
    df.set_index('Trial number', inplace=True)
    print(df)
    baseline_rows = df.loc[df['baseline_alarm'] == True]
    print(baseline_rows)
    baseline_tf_series = baseline_rows['True/False']

    baseline_fp_rate = len(
        baseline_tf_series[lambda x: x == 'False alarm']) / len(baseline_tf_series)

    print('%s / %s = %s' % (len(baseline_tf_series[lambda x: x == 'False alarm']),
                            len(baseline_tf_series), baseline_fp_rate))
    print(baseline_fp_rate)

    canonicalization_rows = df.loc[df['canonicalization_alarm'] == True]
    canonicalization_tf_series = canonicalization_rows['True/False']

    canonicalization_fp_rate = len(
        canonicalization_tf_series[lambda x: x == 'False alarm']) / len(canonicalization_tf_series)

    print('%s / %s = %s' % (len(canonicalization_tf_series[lambda x: x == 'False alarm']),
                            len(canonicalization_tf_series), canonicalization_fp_rate))
    print(canonicalization_fp_rate)

    taint_analysis_rows = df.loc[df['taint_analysis_alarm'] == True]
    taint_analysis_tf_series = taint_analysis_rows['True/False']

    taint_analysis_fp_rate = len(
        taint_analysis_tf_series[lambda x: x == 'False alarm']) / len(taint_analysis_tf_series)

    print('%s / %s = %s' % (len(taint_analysis_tf_series[lambda x: x == 'False alarm']),
                            len(taint_analysis_tf_series), taint_analysis_fp_rate))
    print(taint_analysis_fp_rate)

    dependency_rows = df.loc[df['dependency_alarm'] == True]
    dependency_tf_series = dependency_rows['True/False']

    dependency_fp_rate = len(
        dependency_tf_series[lambda x: x == 'False alarm']) / len(dependency_tf_series)

    print('%s / %s = %s' % (len(dependency_tf_series[lambda x: x == 'False alarm']),
                            len(dependency_tf_series), dependency_fp_rate))
    print(dependency_fp_rate)
