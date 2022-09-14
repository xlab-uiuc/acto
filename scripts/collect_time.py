import argparse
import datetime
import re  
import glob
import json
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Counts number of fields in testrun dirs')
    parser.add_argument('--testrun-dir', help='Directory to check', required=True)

    args = parser.parse_args()
    trial_dirs = glob.glob(args.testrun_dir + '/*')

    total_testing_time = datetime.timedelta()
    total_steps = 0
    for trial_dir in sorted(trial_dirs):
        if not os.path.isdir(trial_dir):
            continue
        print(trial_dir)

        # aggregate the total number of steps
        cr_files = glob.glob(trial_dir + '/mutated-*.yaml')
        total_steps += len(cr_files)

        # aggregate the total time
        # parse the duration
        with open(trial_dir + '/result.json', 'r') as result_file:
            result = json.load(result_file)
            duration_str = result['duration']
            duration = datetime.datetime.strptime(duration_str, '%H:%M:%S')
            duration_delta = datetime.timedelta(hours=duration.hour, minutes=duration.minute, seconds=duration.second)
            total_testing_time += duration_delta
    
    print('Total time: %s' % str(total_testing_time))

    with open(args.testrun_dir + '/test.log', 'r') as test_log:
        lines = test_log.readlines()

        timestamp_sequence = []
        log_regex = r'^\s*'
        log_regex += r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
        log_regex += r'\s*'

        for line in lines:
            match = re.search(log_regex, line)
            if match:
                timestamp_sequence.append(match.group(1))

        start_timestamp = datetime.datetime.strptime(timestamp_sequence[0], '%Y-%m-%d %H:%M:%S,%f')
        end_timestamp = datetime.datetime.strptime(timestamp_sequence[-1], '%Y-%m-%d %H:%M:%S,%f')
        total_time = end_timestamp - start_timestamp
        print('Total time: %s' % str(total_time))
