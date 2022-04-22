import glob
import time
import argparse
import json

if __name__ == "__main__":
    t = time.localtime()

    parser = argparse.ArgumentParser(
        description='Collect test results and merge them')
    
    total_result = {}
    jsons = glob.glob('./*/result.json')
    for fname in jsons:
        with open(fname, 'r') as json_file:
            result = json.load(json_file)
            total_result[result['trial_num']] = result

    with open('total_result.json', 'w') as fout:
        json.dump(total_result, fout, indent=4, sort_keys=True)

    summary = {'SystemState': {}, 'ErrorLog': {}}
    for trial_num, result in total_result.items():
        if 'oracle' in result:
            oracle = result['oracle']
            if oracle not in summary:
                summary[oracle] = {}
            path_str = ' '.join(str(i) for i in result['input_delta']['path'])
            if path_str not in summary[oracle]:
                summary[oracle][path_str] = {}
            msg = result['message']
            if msg not in summary[oracle][path_str]:
                summary[oracle][path_str][msg] = []
            summary[oracle][path_str][msg].append(result)

    with open('summary.json', 'w') as summary_file:
        json.dump(summary, summary_file, indent=4, sort_keys=True)
        

