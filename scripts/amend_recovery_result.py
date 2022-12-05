from datetime import datetime
import glob
import json
import multiprocessing
import os
import sys
import queue
from deepdiff import DeepDiff

def amend_result(workqueue):
    while True:
        try:
            json_path = workqueue.get(block=False)
        except queue.Empty:
            break
        print(json_path)
        changed = False
        json_instance = None
        with open(json_path, 'r') as json_file:
            json_instance = json.load(json_file)

            if 'error' in json_instance:
                if json_instance['error']['recovery_result'] == None:
                    recovery_result = 'Pass'
                elif json_instance['error']['recovery_result'] == 'Pass':
                    recovery_result = 'Pass'
                elif isinstance(json_instance['error']['recovery_result'], dict):
                    changed = True
                    recovery_result = json_instance['error']['recovery_result']['delta']
                    curr_system_state = json_instance['error']['recovery_result']['to']
                    prev_system_state = json_instance['error']['recovery_result']['from']

                    del curr_system_state['endpoints']
                    del prev_system_state['endpoints']
                    del curr_system_state['job']
                    del prev_system_state['job']

                    # remove pods that belong to jobs from both states to avoid observability problem
                    curr_pods = curr_system_state['pod']
                    prev_pods = prev_system_state['pod']
                    curr_system_state['pod'] = {
                        k: v
                        for k, v in curr_pods.items()
                        if v['metadata']['owner_references'][0]['kind'] != 'Job'
                    }
                    prev_system_state['pod'] = {
                        k: v
                        for k, v in prev_pods.items()
                        if v['metadata']['owner_references'][0]['kind'] != 'Job'
                    }

                    for name, obj in prev_system_state['secret'].items():
                        if 'data' in obj and obj['data'] != None:
                            for key, data in obj['data'].items():
                                try:
                                    obj['data'][key] = json.loads(data)
                                except:
                                    pass

                    for name, obj in curr_system_state['secret'].items():
                        if 'data' in obj and obj['data'] != None:
                            for key, data in obj['data'].items():
                                try:
                                    obj['data'][key] = json.loads(data)
                                except:
                                    pass

                    # remove custom resource from both states
                    curr_system_state.pop('custom_resource_spec', None)
                    prev_system_state.pop('custom_resource_spec', None)
                    curr_system_state.pop('custom_resource_status', None)
                    prev_system_state.pop('custom_resource_status', None)

                    # remove fields that are not deterministic
                    exclude_paths = [
                        r".*\['metadata'\]\['managed_fields'\]",
                        r".*\['metadata'\]\['creation_timestamp'\]",
                        r".*\['metadata'\]\['resource_version'\]",
                        r".*\['metadata'\].*\['uid'\]",
                        r".*\['metadata'\]\['generation'\]",
                        r".*\['metadata'\]\['annotations'\]",
                        r".*\['metadata'\]\['annotations'\]\['.*last-applied.*'\]",
                        r".*\['metadata'\]\['annotations'\]\['.*\.kubernetes\.io.*'\]",
                        r".*\['metadata'\]\['labels'\]\['.*revision.*'\]",
                        r".*\['metadata'\]\['labels'\]\['owner-rv'\]",
                        r".*\['status'\]",
                        r".*\['spec'\]\['init_containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]",
                        r".*\['spec'\]\['containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]",
                        r".*\['spec'\]\['volumes'\]\[.*\]\['name'\]",
                        r".*\[.*\]\['node_name'\]",
                        r".*\['version'\]",
                        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['uid'\]",
                        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['resource_version'\]",
                        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['ip'\]",
                        r".*\['cluster_ip'\]",
                        r".*\['cluster_i_ps'\].*",
                    ]

                    diff = DeepDiff(prev_system_state, curr_system_state, exclude_regex_paths=exclude_paths)

                    if diff == None:
                        json_instance['error']['recovery_result'] = 'Pass'
                    else:

                        j = diff.to_json(default_mapping={datetime: lambda x: x.isoformat()})
                        if j != '{}':
                            json_instance['error']['recovery_result'] = {
                                'delta': diff.to_json(default_mapping={datetime: lambda x: x.isoformat()}),
                                'from': prev_system_state,
                                'to': curr_system_state,
                            }
                        else:
                            json_instance['error']['recovery_result'] = 'Pass'
            else:
                recovery_result = 'Pass'

        if changed:
            with open(json_path, 'w') as json_file:
                json.dump(json_instance, json_file, indent=4)

if __name__ == '__main__':
    result_folder = sys.argv[1]
    recovery_results = glob.glob(os.path.join(result_folder, '*', 'result.json'))

    mp_manager = multiprocessing.Manager()
    workqueue = multiprocessing.Queue()

    for json_path in sorted(recovery_results):
        workqueue.put(json_path)

    workers = [
        multiprocessing.Process(target=amend_result,
                                args=(workqueue, ))
        for _ in range(8)
    ]

    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join()