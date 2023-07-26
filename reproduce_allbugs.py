import argparse
from enum import Enum
import multiprocessing
import queue
from typing import List
from tabulate import tabulate
from acto.reproduce import reproduce, reproduce_postdiff
from test.utils import BugConfig, all_bugs

class BugCateogry(str, Enum):
    UNDESIRED_STATE = 'undesired_state'
    SYSTEM_ERROR = 'system_error'
    OPERATOR_ERROR = 'operator_error'
    RECOVERY_FAILURE = 'recovery_failure'

    def __str__(self) -> str:
        return self.value


class ReproWorker:

    def __init__(self, workqueue: multiprocessing.Queue, acto_namespace: int) -> None:
        self._workqueue = workqueue
        self._acto_namespace = acto_namespace

    def run(self):
        while True:
            try:
                bug_tuple = self._workqueue.get(block=False)
            except queue.Empty:
                break

            operator, bug_id, bug_config = bug_tuple
            repro_dir = bug_config.dir
            work_dir = f'testrun-{bug_id}'
            operator_config = f'data/{operator}/config.json'

            if bug_config.difftest:
                reproduce(work_dir, repro_dir, operator_config, cluster_runtime='KIND', acto_namespace=self._acto_namespace)
                if reproduce_postdiff(work_dir, operator_config, cluster_runtime='KIND', acto_namespace=self._acto_namespace):
                    print(f"Bug {bug_id} reproduced!")
                    reproduce_results[operator][bug_config.category] += 1
                    continue
                else:
                    print(f"Bug {bug_id} not reproduced!")
                    failed_reproductions[bug_id] = True
                    continue
            else:
                if reproduce(work_dir, repro_dir, operator_config, cluster_runtime='KIND', acto_namespace=self._acto_namespace):
                    print(f"Bug {bug_id} reproduced!")
                    reproduce_results[operator][bug_config.category] += 1
                    continue
                else:
                    print(f"Bug {bug_id} not reproduced!")
                    failed_reproductions[bug_id] = True
                    continue


if __name__ == '__main__':
    reproduce_results = {}
    failed_reproductions = {}
    parser = argparse.ArgumentParser()
    parser.add_argument('--num-workers', '-n', dest='num_workers', type=int, default=1)
    args = parser.parse_args()

    workqueue = multiprocessing.Queue()

    for operator, bugs in all_bugs.items():
        reproduce_results[operator] = {
            BugCateogry.UNDESIRED_STATE: 0,
            BugCateogry.SYSTEM_ERROR: 0,
            BugCateogry.OPERATOR_ERROR: 0,
            BugCateogry.RECOVERY_FAILURE: 0,
        }
        for bug_id, bug_config in bugs.items():
            workqueue.put((operator, bug_id, bug_config))

    workers: List[ReproWorker] = []
    for i in range(args.num_workers):
        worker = ReproWorker(workqueue, i)
        workers.append(worker)

    processes = []
    for worker in workers:
        p = multiprocessing.Process(target=worker.run)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    table = []
    for operator, reproduce_result in reproduce_results.items():
        table.append([operator, reproduce_result[BugCateogry.UNDESIRED_STATE], reproduce_result[BugCateogry.SYSTEM_ERROR], reproduce_result[BugCateogry.OPERATOR_ERROR], reproduce_result[BugCateogry.RECOVERY_FAILURE]])

    print(tabulate(table, headers=['Operator', 'Undesired State', 'System Error', 'Operator Error', 'Recovery Failure']))