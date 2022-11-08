import csv
import glob
import json
import sys
import os
import pandas

if __name__ == '__main__':
    result_folder = sys.argv[1]
    json_paths = glob.glob(os.path.join(result_folder, '*', 'post-result-*.json'))

    with open(os.path.join(result_folder, 'result.csv'), 'w') as result_file:
        writer = csv.writer(result_file, delimiter=',')
        writer.writerow([
            'Generation number', 'Alarm', 'Crash Result', 'Recovery Result', 'State Result',
            'Custom Result', 'True/False alarm', 'Category', 'Comment'
        ])

        for json_path in json_paths:
            with open(json_path, 'r') as json_file:
                json_instance = json.load(json_file)

                post_result = json_instance['post_result']
                if 'error' in post_result:

                    if post_result['error']['crash_result'] == None:
                        crash_result = 'Pass'
                    elif isinstance(post_result['error']['crash_result'], dict):
                        crash_result = post_result['error']['crash_result']['message']
                    elif post_result['error']['crash_result'] == 'Pass':
                        crash_result = 'Pass'
                        
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

                writer.writerow([
                    '%s' % post_result['trial_num'] + '-' + '%s' % post_result['error']['generation'],
                    json_instance['alarm'],
                    '%s' % crash_result,
                    '%s' % recovery_result,
                    '%s' % post_state_result,
                    '%s' % custom_result,
                ])