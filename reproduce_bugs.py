import argparse
import multiprocessing
import os
import queue
import sys
import threading
from datetime import datetime
from test import oat_ae_utils
from typing import Tuple

from tabulate import tabulate

from acto.reproduce import (
    reproduce,
    reproduce_fault_injection,
    reproduce_postdiff,
)
from acto.utils import error_handler


class ReproWorker:
    """Worker for reproducing bugs"""

    def __init__(
        self,
        repro_result_dir: str,
        workqueue: multiprocessing.Queue,
        acto_namespace: int,
    ) -> None:
        self._repro_result_dir = repro_result_dir
        self._workqueue = workqueue
        self._acto_namespace = acto_namespace

    def run(self, reproduce_results: dict, failed_reproductions: dict) -> None:
        """Run the reproduction worker"""
        while True:
            try:
                bug_tuple: tuple[
                    oat_ae_utils.OperatorPrettyName,
                    str,
                    oat_ae_utils.OatBugConfig,
                ] = self._workqueue.get(block=True, timeout=5)
            except queue.Empty:
                break

            retry = False
            for i in range(3):
                retry = False
                operator, bug_id, bug_config = bug_tuple
                repro_dir = bug_config.path
                work_dir = f"{self._repro_result_dir}/testrun-{bug_id}"
                operator_config = oat_ae_utils.OperatorToConfigMapping[operator]

                if bug_id == "K8SPSMDB-1333":
                    # K8SPSMDB-1333 is a problem that happens every time when
                    # deploying the MongoDB cluster. We intentionally skip it
                    # for other runs so that we can detect other bugs.
                    # The special config does not skip this bug.
                    operator_config = (
                        "data/percona-server-mongodb-operator/"
                        + "v1-16-0/func-only-1333.json"
                    )
                elif bug_id == "tidbop-98":
                    operator_config = (
                        "data/tidb-operator/v1-6-0/func-only-no-oracle.json"
                    )
                elif bug_id == "tidbop-5729":
                    operator_config = (
                        "data/tidb-operator/v1-6-0/func-only-tikv.json"
                    )
                elif bug_id == "kafkaop-10231":
                    operator_config = (
                        "data/strimzi-kafka-operator/v0-45-0/func-only-zk.json"
                    )
                elif bug_id == "cassop-694":
                    operator_config = (
                        "data/cass-operator/v1-22/func-only-users.json"
                    )

                reproduced: bool = False
                normal_run_result = reproduce(
                    work_dir,
                    repro_dir,
                    operator_config,
                    cluster_runtime="KIND",
                    acto_namespace=self._acto_namespace,
                    secret_config=bug_config.secrets,
                )
                if bug_config.difftest:
                    if reproduce_postdiff(
                        work_dir,
                        operator_config,
                        cluster_runtime="KIND",
                        acto_namespace=self._acto_namespace,
                    ):
                        reproduced = True
                    else:
                        retry = True
                        print(f"Bug {bug_id} not reproduced!")
                elif bug_config.fault:
                    if reproduce_fault_injection(
                        work_dir,
                        operator_config,
                        oat_ae_utils.OperatorToFIConfigMapping[operator],
                    ):
                        reproduced = True
                    else:
                        retry = True
                        print(f"Bug {bug_id} not reproduced!")

                last_error = normal_run_result[-1]
                if last_error is not None and last_error.is_error():
                    reproduced = True

                # check if reproduced for table 5, and write results
                if reproduced:
                    print(f"Bug {bug_id} reproduced!")
                    print(f"Bug category: {bug_config.category}")
                    reproduce_results[operator][bug_config.category] += 1
                    break

                if i < 3 and retry:
                    print(f"Bug {bug_id} not reproduced! Trying ({i+1}/3)")
                else:
                    print(f"Bug {bug_id} not reproduced after 3 attempts.")
                    failed_reproductions[bug_id] = True


def main() -> None:
    """Main function"""
    # Register custom exception hook
    sys.excepthook = error_handler.handle_excepthook
    threading.excepthook = error_handler.thread_excepthook

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--num-workers", "-n", dest="num_workers", type=int, default=1
    )
    parser.add_argument(
        "--bug-id", dest="bug_id", type=str, required=False, default=None
    )
    args = parser.parse_args()

    produce_table = True

    bug_id_map: dict[
        str, Tuple[oat_ae_utils.OperatorPrettyName, oat_ae_utils.OatBugConfig]
    ] = {}
    for operator, bugs in oat_ae_utils.ALL_BUGS.items():
        for bug_id, bug_config in bugs.items():
            bug_id_map[bug_id] = (operator, bug_config)
            # check if path exists
            if not os.path.exists(bug_config.path):
                print(
                    f"Path {bug_config.path} for bug {bug_id} does not exist! Skipping."
                )
                continue

    arg_bug_id = args.bug_id
    if arg_bug_id is not None and isinstance(arg_bug_id, str):
        (operator, bug_config) = bug_id_map[arg_bug_id]
        print(f"Reproducing bug {arg_bug_id} in {operator}!")
        to_reproduce = {operator: {arg_bug_id: bug_config}}
        produce_table = False
    else:
        print("Reproducing all bugs!")
        to_reproduce = oat_ae_utils.ALL_BUGS

    manager = multiprocessing.Manager()
    reproduce_results = manager.dict()
    failed_reproductions = manager.dict()

    total_reproduced = 0
    repro_result_dir = os.path.join(
        os.getcwd(),
        f"repro_results-{datetime.now().strftime('%Y-%m-%d-%H-%M')}",
    )

    workqueue: multiprocessing.Queue = multiprocessing.Queue()

    for operator, bugs in to_reproduce.items():
        reproduce_results[operator] = manager.dict()
        reproduce_results[operator][
            oat_ae_utils.BugCategory.OPERATION_SEMANTICS
        ] = 0
        reproduce_results[operator][
            oat_ae_utils.BugCategory.STATE_OBSERVABILITY
        ] = 0
        reproduce_results[operator][
            oat_ae_utils.BugCategory.VERSION_COMPATIBILITY
        ] = 0
        reproduce_results[operator][oat_ae_utils.BugCategory.ERROR_HANDLING] = 0
        reproduce_results[operator][oat_ae_utils.BugCategory.BY_PRODUCT] = 0

        for bug_id, bug_config in bugs.items():
            workqueue.put((operator, bug_id, bug_config))

    workers: list[ReproWorker] = []
    for i in range(args.num_workers):
        worker = ReproWorker(repro_result_dir, workqueue, i)
        workers.append(worker)

    processes = []
    for worker in workers:
        p = multiprocessing.Process(
            target=worker.run,
            args=(
                reproduce_results,
                failed_reproductions,
            ),
        )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    if produce_table:
        print("Reproduction results:")
        # aggregate results from each worker
        for operator, results in reproduce_results.items():
            for _, count in results.items():
                total_reproduced += count

        table7 = []
        for operator, reproduce_result in reproduce_results.items():
            table7.append(
                [
                    operator,
                    reproduce_result[
                        oat_ae_utils.BugCategory.OPERATION_SEMANTICS
                    ],
                    reproduce_result[
                        oat_ae_utils.BugCategory.STATE_OBSERVABILITY
                    ],
                    reproduce_result[
                        oat_ae_utils.BugCategory.VERSION_COMPATIBILITY
                    ],
                    reproduce_result[oat_ae_utils.BugCategory.ERROR_HANDLING],
                    reproduce_result[oat_ae_utils.BugCategory.BY_PRODUCT],
                    sum(reproduce_result.values()),
                ]
            )

        table7 = sorted(table7, key=lambda x: x[0])

        table7.append(
            [
                "Total",
                sum(
                    reproduce_result[
                        oat_ae_utils.BugCategory.OPERATION_SEMANTICS
                    ]
                    for reproduce_result in reproduce_results.values()
                ),
                sum(
                    reproduce_result[
                        oat_ae_utils.BugCategory.STATE_OBSERVABILITY
                    ]
                    for reproduce_result in reproduce_results.values()
                ),
                sum(
                    reproduce_result[
                        oat_ae_utils.BugCategory.VERSION_COMPATIBILITY
                    ]
                    for reproduce_result in reproduce_results.values()
                ),
                sum(
                    reproduce_result[oat_ae_utils.BugCategory.ERROR_HANDLING]
                    for reproduce_result in reproduce_results.values()
                ),
                sum(
                    reproduce_result[oat_ae_utils.BugCategory.BY_PRODUCT]
                    for reproduce_result in reproduce_results.values()
                ),
                total_reproduced,
            ]
        )

        print(
            tabulate(
                table7,
                headers=[
                    "Operator",
                    oat_ae_utils.BugCategory.OPERATION_SEMANTICS,
                    oat_ae_utils.BugCategory.STATE_OBSERVABILITY,
                    oat_ae_utils.BugCategory.VERSION_COMPATIBILITY,
                    oat_ae_utils.BugCategory.ERROR_HANDLING,
                    oat_ae_utils.BugCategory.BY_PRODUCT,
                    "Total",
                ],
            )
        )
        with open("table7.txt", "w", encoding="utf-8") as table7_f:
            table7_f.write(
                tabulate(
                    table7,
                    headers=[
                        "Operator",
                        oat_ae_utils.BugCategory.OPERATION_SEMANTICS,
                        oat_ae_utils.BugCategory.STATE_OBSERVABILITY,
                        oat_ae_utils.BugCategory.VERSION_COMPATIBILITY,
                        oat_ae_utils.BugCategory.ERROR_HANDLING,
                        oat_ae_utils.BugCategory.BY_PRODUCT,
                        "Total",
                    ],
                )
            )

        print(f"Total reproduced: {total_reproduced}")
        print(f"Failed reproductions: {len(failed_reproductions)}")
        if len(failed_reproductions) > 0:
            print("Failed reproductions:")
            for bug_id in failed_reproductions:
                print(f"  - {bug_id}")


if __name__ == "__main__":
    main()
