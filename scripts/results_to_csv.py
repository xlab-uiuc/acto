import csv
import glob
import json
import sys
import os
import pandas

if __name__ == '__main__':
    result_folder = sys.argv[1]
    json_paths = glob.glob(os.path.join(result_folder, '*', 'result.json'))

    with open(os.path.join(result_folder, 'result.csv'), 'w') as result_file:
        writer = csv.writer(result_file, delimiter=',')
        writer.writerow(['Trial number', 'Oracle type', 'Message', 'Input path', 'True/False alarm', 'Comment'])

        for json_path in json_paths:
            with open(json_path, 'r') as json_file:
                json_instance = json.load(json_file)
                if 'input_delta' not in json_instance or json_instance['input_delta'] == None:
                    path = None
                else:
                    path = json_instance['input_delta']['path']
                writer.writerow(['%04d'%json_instance['trial_num'], None if 'oracle' not in json_instance else json_instance['oracle'], None if 'message' not in json_instance else json_instance['message'], path])

    df = pandas.read_csv(os.path.join(result_folder, 'result.csv'))
    df.sort_values(['Trial number'], inplace=True)
    df.to_csv(os.path.join(result_folder, 'result.csv'), index=False)