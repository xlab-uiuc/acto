import argparse
from datetime import datetime
from enum import Enum
import glob
import json
import multiprocessing
import os
import queue
from typing import Dict, List, Tuple
from tabulate import tabulate
from acto.checker.impl.health import HealthChecker
from acto.common import PassResult
from acto.reproduce import reproduce, reproduce_postdiff
from acto.snapshot import EmptySnapshot
from produce_table_6 import generate_table_6
from test.utils import BugConfig, all_bugs, operator_pretty_name_mapping


class BugCateogry(str, Enum):
    UNDESIRED_STATE = 'undesired_state'
    SYSTEM_ERROR = 'system_error'
    OPERATOR_ERROR = 'operator_error'
    RECOVERY_FAILURE = 'recovery_failure'

    def __str__(self) -> str:
        return self.value


def check_postdiff_runtime_error(workdir_path: str) -> bool:
    post_diff_test_dir = os.path.join(workdir_path, 'post_diff_test')
    compare_results = glob.glob(os.path.join(post_diff_test_dir, 'compare-results-*.json'))
    if len(compare_results) == 0:
        return False
    else:
        for compare_result in compare_results:
            with open(compare_result) as f:
                result = json.load(f)[0]
                to_state = result['to']
                snapshot = EmptySnapshot({})
                snapshot.system_state = to_state
                health_result = HealthChecker().check(0, snapshot, {})
                if not isinstance(health_result, PassResult):
                    return True

    return False


class ReproWorker:

    def __init__(self, repro_result_dir: str, workqueue: multiprocessing.Queue, acto_namespace: int) -> None:
        self._repro_result_dir = repro_result_dir
        self._workqueue = workqueue
        self._acto_namespace = acto_namespace

    def run(self, reproduce_results, table_7_results):
        while True:
            try:
                bug_tuple: Tuple[str, str, BugConfig] = self._workqueue.get(block=True, timeout=5)
            except queue.Empty:
                break

            retry = False
            for i in range(3):
                retry = False
                operator, bug_id, bug_config = bug_tuple
                repro_dir = bug_config.dir
                work_dir = f'{self._repro_result_dir}/testrun-{bug_id}'
                operator_config = f'data/{operator}/config.json'

                reproduced: bool = False
                normal_run_result = reproduce(work_dir,
                                              repro_dir,
                                              operator_config,
                                              cluster_runtime='KIND',
                                              acto_namespace=self._acto_namespace)
                if bug_config.difftest:
                    if bug_config.diffdir != None:
                        diff_repro_dir = bug_config.diffdir
                        work_dir = f'{self._repro_result_dir}/testrun-{bug_id}-diff'
                        reproduce(work_dir,
                                  diff_repro_dir,
                                  operator_config,
                                  cluster_runtime='KIND',
                                  acto_namespace=self._acto_namespace)
                    if reproduce_postdiff(work_dir,
                                          operator_config,
                                          cluster_runtime='KIND',
                                          acto_namespace=self._acto_namespace):
                        reproduced = True
                        table_7_results['diff_oracle'] += 1
                    else:
                        retry = True
                        print(f"Bug {bug_id} not reproduced!")
                        failed_reproductions[bug_id] = True

                if bug_config.declaration:
                    if len(normal_run_result) != 0:
                        last_error = normal_run_result[-1]
                        if last_error.state_result != None and not isinstance(
                                last_error.state_result, PassResult):
                            reproduced = True
                            table_7_results['declaration_oracle'] += 1
                        elif last_error.recovery_result != None and not isinstance(
                                last_error.recovery_result, PassResult):
                            reproduced = True
                            table_7_results['declaration_oracle'] += 1
                    else:
                        retry = True
                        print(f"Bug {bug_id} not reproduced!")
                        failed_reproductions[bug_id] = True

                if bug_config.recovery:
                    if len(normal_run_result) != 0:
                        last_error = normal_run_result[-1]
                        if last_error.recovery_result != None and not isinstance(
                                last_error.recovery_result, PassResult):
                            reproduced = True
                            table_7_results['recovery_oracle'] += 1
                        elif last_error.state_result != None and not isinstance(
                                last_error.state_result, PassResult):
                            reproduced = True
                            table_7_results['recovery_oracle'] += 1
                    else:
                        retry = True
                        print(f"Bug {bug_id} not reproduced!")
                        failed_reproductions[bug_id] = True

                if bug_config.runtime_error:
                    if bug_config.difftest and check_postdiff_runtime_error(work_dir):
                        reproduced = True
                        table_7_results['runtime_oracle'] += 1
                    elif len(normal_run_result) != 0:
                        last_error = normal_run_result[-1]
                        if last_error.health_result != None and not isinstance(
                                last_error.health_result, PassResult):
                            reproduced = True
                            table_7_results['runtime_oracle'] += 1
                    else:
                        retry = True
                        print(f"Bug {bug_id} not reproduced!")
                        failed_reproductions[bug_id] = True

                # check if reproduced for table 5, and write results
                if reproduced and not retry:
                    print(f"Bug {bug_id} reproduced!")
                    print(f"Bug category: {bug_config.category}")
                    reproduce_results[operator][bug_config.category] += 1
                    break
                elif i < 2:
                    print(f"Bug {bug_id} not reproduced! Trying ({i+1}/3)")
                else:
                    failed_reproductions[bug_id] = True



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--num-workers', '-n', dest='num_workers', type=int, default=1)
    parser.add_argument('--bug-id', dest='bug_id', type=str, required=False, default=None)
    args = parser.parse_args()

    produce_table = True

    bug_id_map: Dict[str, Tuple[str, BugConfig]] = {}
    for operator, bugs in all_bugs.items():
        for bug_id, bug_config in bugs.items():
            bug_id_map[bug_id] = (operator, bug_config)

    if args.bug_id:
        (operator, bug_config) = bug_id_map[args.bug_id]
        print(f"Reproducing bug {args.bug_id} in {operator_pretty_name_mapping[operator]}!")
        to_reproduce = {operator: {args.bug_id: bug_config}}
        produce_table = False
    else:
        print(f"Reproducing all bugs!")
        to_reproduce = all_bugs

    manager = multiprocessing.Manager()
    reproduce_results = manager.dict()
    table_7_results = manager.dict()
    table_7_results['declaration_oracle'] = 0
    table_7_results['runtime_oracle'] = 0
    table_7_results['recovery_oracle'] = 0
    table_7_results['diff_oracle'] = 0

    failed_reproductions = {}
    total_reproduced = 0
    repro_result_dir = os.path.join(os.getcwd(), 'repro_results-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M') )

    workqueue = multiprocessing.Queue()

    for operator, bugs in to_reproduce.items():
        reproduce_results[operator] = manager.dict()
        reproduce_results[operator][BugCateogry.UNDESIRED_STATE] = 0
        reproduce_results[operator][BugCateogry.SYSTEM_ERROR] = 0
        reproduce_results[operator][BugCateogry.OPERATOR_ERROR] = 0
        reproduce_results[operator][BugCateogry.RECOVERY_FAILURE] = 0

        for bug_id, bug_config in bugs.items():
            workqueue.put((operator, bug_id, bug_config))

    workers: List[ReproWorker] = []
    for i in range(args.num_workers):
        worker = ReproWorker(repro_result_dir, workqueue, i)
        workers.append(worker)

    processes = []
    for worker in workers:
        p = multiprocessing.Process(target=worker.run, args=(reproduce_results, table_7_results))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    if produce_table:
        print("Reproduction results:")
        # aggregate results from each worker
        for operator, results in reproduce_results.items():
            for category, count in results.items():
                total_reproduced += count

        reproduce_results['knative-operator'] = manager.dict()
        reproduce_results['knative-operator'][
            BugCateogry.UNDESIRED_STATE] = reproduce_results['knative-operator-serving'][
                BugCateogry.UNDESIRED_STATE] + reproduce_results['knative-operator-eventing'][
                    BugCateogry.UNDESIRED_STATE]
        reproduce_results['knative-operator'][
            BugCateogry.SYSTEM_ERROR] = reproduce_results['knative-operator-serving'][
                BugCateogry.SYSTEM_ERROR] + reproduce_results['knative-operator-eventing'][
                    BugCateogry.SYSTEM_ERROR]
        reproduce_results['knative-operator'][
            BugCateogry.OPERATOR_ERROR] = reproduce_results['knative-operator-serving'][
                BugCateogry.OPERATOR_ERROR] + reproduce_results['knative-operator-eventing'][
                    BugCateogry.OPERATOR_ERROR]
        reproduce_results['knative-operator'][
            BugCateogry.RECOVERY_FAILURE] = reproduce_results['knative-operator-serving'][
                BugCateogry.RECOVERY_FAILURE] + reproduce_results['knative-operator-eventing'][
                    BugCateogry.RECOVERY_FAILURE]

        del reproduce_results['knative-operator-serving']
        del reproduce_results['knative-operator-eventing']

        table5 = []
        for operator, reproduce_result in reproduce_results.items():
            table5.append([
                operator_pretty_name_mapping[operator], reproduce_result[BugCateogry.UNDESIRED_STATE],
                reproduce_result[BugCateogry.SYSTEM_ERROR],
                reproduce_result[BugCateogry.OPERATOR_ERROR],
                reproduce_result[BugCateogry.RECOVERY_FAILURE],
                sum(reproduce_result.values())
            ])

        table5 = sorted(table5, key=lambda x: x[0])

        table5.append([
            'Total',
            sum([
                reproduce_result[BugCateogry.UNDESIRED_STATE]
                for reproduce_result in reproduce_results.values()
            ]),
            sum([
                reproduce_result[BugCateogry.SYSTEM_ERROR]
                for reproduce_result in reproduce_results.values()
            ]),
            sum([
                reproduce_result[BugCateogry.OPERATOR_ERROR]
                for reproduce_result in reproduce_results.values()
            ]),
            sum([
                reproduce_result[BugCateogry.RECOVERY_FAILURE]
                for reproduce_result in reproduce_results.values()
            ]), total_reproduced
        ])

        print(
            tabulate(table5,
                    headers=[
                        'Operator', 'Undesired State', 'System Error', 'Operator Error',
                        'Recovery Failure', 'Total'
                    ]))
        with open('table5.txt', 'w') as table5_f:
            table5_f.write(
                tabulate(table5,
                        headers=[
                            'Operator', 'Undesired State', 'System Error', 'Operator Error',
                            'Recovery Failure', 'Total'
                        ]))
            
        generate_table_6()

        print(f"Total reproduced: {total_reproduced}")
        table7 = []
        table7.append([
            'Consistency oracle',
            f"{table_7_results['declaration_oracle']} ({table_7_results['declaration_oracle']/total_reproduced:.2%})"
        ])
        table7.append([
            'Differential oracle for normal state transition',
            f"{table_7_results['diff_oracle']} ({table_7_results['diff_oracle']/total_reproduced:.2%})"
        ])
        table7.append([
            'Differential oracle for rollback state transition',
            f"{table_7_results['recovery_oracle']} ({table_7_results['recovery_oracle']/total_reproduced:.2%})"
        ])
        table7.append([
            'Regular error check (e.g., exceptions, error codes)',
            f"{table_7_results['runtime_oracle']} ({table_7_results['runtime_oracle']/total_reproduced:.2%})"
        ])
        print(tabulate(table7, headers=['Test Oracle', '# Bugs (Percentage)']))
        with open('table7.txt', 'w') as table7_f:
            table7_f.write(tabulate(table7, headers=['Test Oracle', '# Bugs (Percentage)']))