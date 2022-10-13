import csv
import glob
import json
import sys
import os
import pandas

if __name__ == '__main__':
    result_folder = sys.argv[1]
    json_paths = glob.glob(os.path.join(result_folder, '*', 'post_result.json'))
    recovery_paths = glob.glob(os.path.join(result_folder, '*', 'recovery_result.json'))

    with open(os.path.join(result_folder, 'result.csv'), 'w') as result_file:
        writer = csv.writer(result_file, delimiter=',')
        writer.writerow([
            'Trial number', 'Original Oracle type', 'Original Message', 'Original Input path',
            'Post Oracle type', 'Post Message', 'Post Input path', 'True/False alarm', 'Category',
            'Comment'
        ])

        for recovery_path in recovery_paths:
            with open(recovery_path, 'r') as recovery_file:
                recovery_result = json.load(recovery_file)

                writer.writerow([
                    '%s' % recovery_path, 'Recovery',
                    '%s' % recovery_result['delta'], '', 'Recovery',
                    '%s' % recovery_result['delta'], ''
                ])

        for json_path in json_paths:
            with open(json_path, 'r') as json_file:
                json_instance = json.load(json_file)

                original_result = json_instance['original_result']
                post_result = json_instance['post_result']
                if 'input_delta' not in original_result or original_result['input_delta'] == None:
                    original_path = None
                else:
                    original_path = original_result['input_delta']['path']

                if 'input_delta' not in post_result or post_result['input_delta'] == None:
                    post_path = None
                else:
                    post_path = post_result['input_delta']['path']

                writer.writerow([
                    '%s' % original_result['trial_num'],
                    None if 'oracle' not in original_result else original_result['oracle'],
                    None if 'message' not in original_result else original_result['message'],
                    original_path,
                    None if 'oracle' not in post_result else post_result['oracle'],
                    None if 'message' not in post_result else post_result['message'],
                    post_path,
                ])

    df = pandas.read_csv(os.path.join(result_folder, 'result.csv'))
    df.sort_values(['Trial number'], inplace=True)
    df.to_csv(os.path.join(result_folder, 'result.csv'), index=False)