import csv
import glob
import json
import sys
import os
import pandas

if __name__ == '__main__':
    result_folder = sys.argv[1]
    json_paths = glob.glob(os.path.join(result_folder, '*', 'post_result.json'))

    with open(os.path.join(result_folder, 'result.csv'), 'w') as result_file:
        writer = csv.writer(result_file, delimiter=',')
        writer.writerow([
            'Trial number', 'Crash Result', 'Recovery Result', 'Original State Result',
            'Post State Result', 'Custom Result', 'True/False alarm', 'Category', 'Comment'
        ])

        for json_path in json_paths:
            with open(json_path, 'r') as json_file:
                json_instance = json.load(json_file)

                original_result = json_instance['original_result']
                post_result = json_instance['post_result']
                if 'error' in original_result:
                    if original_result['error']['crash_result'] == None:
                        crash_result = 'Pass'
                    elif isinstance(original_result['error']['crash_result'], dict):
                        crash_result = original_result['error']['crash_result']['message']
                    elif original_result['error']['crash_result'] == 'Pass':
                        crash_result = 'Pass'

                    if original_result['error']['recovery_result'] == None:
                        recovery_result = 'Pass'
                    elif isinstance(original_result['error']['recovery_result'], dict):
                        recovery_result = original_result['error']['recovery_result']['delta']
                    elif original_result['error']['recovery_result'] == 'Pass':
                        recovery_result = 'Pass'

                    if original_result['error']['custom_result'] == None:
                        custom_result = 'Pass'
                    elif isinstance(original_result['error']['custom_result'], dict):
                        custom_result = original_result['error']['custom_result']['message']
                    elif original_result['error']['custom_result'] == 'Pass':
                        custom_result = 'Pass'

                    if original_result['error']['state_result'] == None:
                        original_state_result = 'Pass'
                    elif isinstance(original_result['error']['state_result'], dict):
                        original_state_result = original_result['error']['state_result'][
                            'input_delta']['path']
                    elif original_result['error']['state_result'] == 'Pass':
                        original_state_result = 'Pass'
                else:
                    crash_result = 'Pass'
                    recovery_result = 'Pass'
                    original_state_result = 'Pass'
                    custom_result = 'Pass'

                if 'error' in post_result:

                    if post_result['error']['state_result'] == None:
                        post_state_result = 'Pass'
                    elif isinstance(post_result['error']['state_result'], dict):
                        post_state_result = post_result['error']['state_result']['input_delta'][
                            'path']
                    elif post_result['error']['state_result'] == 'Pass':
                        post_state_result = 'Pass'
                else:
                    post_state_result = 'Pass'

                writer.writerow([
                    '%s' % original_result['trial_num'],
                    '%s' % crash_result,
                    '%s' % recovery_result,
                    '%s' % original_state_result,
                    '%s' % post_state_result,
                    '%s' % custom_result,
                ])

    df = pandas.read_csv(os.path.join(result_folder, 'result.csv'))
    df.sort_values(['Trial number'], inplace=True)
    df.to_csv(os.path.join(result_folder, 'result.csv'), index=False)