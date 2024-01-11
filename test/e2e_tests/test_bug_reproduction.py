"""This module contains tests for bug reproduction"""
import multiprocessing
import os
import pathlib
import queue
import random
import unittest
from test.utils import BugConfig, all_bugs, check_postdiff_runtime_error
from typing import Dict, List, Tuple

import pytest

from acto.common import PassResult
from acto.reproduce import reproduce, reproduce_postdiff

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


def run_bug_config(
    operator_name: str, bug_id: str, bug_config: BugConfig, acto_namespace: int
) -> bool:
    """This function tries to reproduce a bug according to the bug config

    Returns:
        if the reproduction is successful
    """
    repro_dir = os.path.join(test_data_dir, bug_config.dir)
    work_dir = f"testrun-{bug_id}"
    operator_config = f"data/{operator_name}/config.json"

    reproduced: bool = False
    normal_run_result = reproduce(
        work_dir,
        repro_dir,
        operator_config,
        cluster_runtime="KIND",
        acto_namespace=acto_namespace,
    )
    if bug_config.difftest:
        if bug_config.diffdir is not None:
            diff_repro_dir = os.path.join(test_data_dir, bug_config.diffdir)
            work_dir = f"testrun-{bug_id}-diff"
            reproduce(
                work_dir,
                diff_repro_dir,
                operator_config,
                cluster_runtime="KIND",
                acto_namespace=acto_namespace,
            )
        if reproduce_postdiff(
            work_dir,
            operator_config,
            cluster_runtime="KIND",
            acto_namespace=acto_namespace,
        ):
            reproduced = True
        else:
            print(f"Bug {bug_id} not reproduced!")
            return False

    if bug_config.declaration:
        if len(normal_run_result) != 0:
            last_error = normal_run_result[-1]
            if last_error.state_result is not None and not isinstance(
                last_error.state_result, PassResult
            ):
                reproduced = True
            elif last_error.recovery_result is not None and not isinstance(
                last_error.recovery_result, PassResult
            ):
                reproduced = True
        else:
            print(f"Bug {bug_id} not reproduced!")
            return False

    if bug_config.recovery:
        if len(normal_run_result) != 0:
            last_error = normal_run_result[-1]
            if last_error.recovery_result is not None and not isinstance(
                last_error.recovery_result, PassResult
            ):
                reproduced = True
            elif last_error.state_result is not None and not isinstance(
                last_error.state_result, PassResult
            ):
                reproduced = True
        else:
            print(f"Bug {bug_id} not reproduced!")
            return False

    if bug_config.runtime_error:
        if bug_config.difftest and check_postdiff_runtime_error(work_dir):
            reproduced = True
        elif len(normal_run_result) != 0:
            last_error = normal_run_result[-1]
            if last_error.health_result is not None and not isinstance(
                last_error.health_result, PassResult
            ):
                reproduced = True
        else:
            print(f"Bug {bug_id} not reproduced!")
            return False

    return reproduced


NUM_RETRY = 3


def run_worker(
    workqueue: multiprocessing.Queue,
    acto_namespace: int,
    reproduction_results: Dict[str, bool],
):
    """This function is a worker that tries to reproduce bugs in the workqueue"""
    while True:
        try:
            bug_tuple: Tuple[str, str, BugConfig] = workqueue.get(
                block=True, timeout=5
            )
        except queue.Empty:
            break

        operator_name, bug_id, bug_config = bug_tuple
        reproduced = False

        for _ in range(NUM_RETRY):
            if run_bug_config(
                operator_name=operator_name,
                bug_id=bug_id,
                bug_config=bug_config,
                acto_namespace=acto_namespace,
            ):
                reproduced = True
                break

        reproduction_results[bug_id] = reproduced


@pytest.mark.all_bug_reproduction
class TestBugReproduction(unittest.TestCase):
    """This class contains tests for bug reproduction"""

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        self._num_workers = 2  # Number of workers to run the test

    def test_all_bugs(self):
        """This function tries to reproduce all bugs in all_bugs"""
        manager = multiprocessing.Manager()
        workqueue = multiprocessing.Queue()

        for operator, bugs in all_bugs.items():
            for bug_id, bug_config in bugs.items():
                workqueue.put((operator, bug_id, bug_config))

        # workers write reproduction results
        reproduction_results: Dict[str, bool] = manager.dict()
        # to this dict. Bug ID -> if success
        processes: List[multiprocessing.Process] = []
        for i in range(self._num_workers):
            p = multiprocessing.Process(
                target=run_worker, args=(workqueue, i, reproduction_results)
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        errors = []
        for bug_id, if_reproduced in reproduction_results.items():
            if not if_reproduced:
                errors.append(bug_id)

        self.assertFalse(errors, f"Test failed with {errors}")


@pytest.mark.single_bug_reproduction
class TestSingleBugReproduction(unittest.TestCase):
    """This class contains tests for single bug reproduction"""

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        self._num_workers = 1  # Number of workers to run the test

    def test_one_bug(self):
        """This function tries to reproduce one bug in all_bugs"""
        manager = multiprocessing.Manager()
        workqueue = multiprocessing.Queue()

        operator, bugs = random.choice(list(all_bugs.items()))
        bug_id, bug_config = random.choice(list(bugs.items()))
        operator, bug_id, bug_config = (
            "cass-operator",
            "cassop-330",
            all_bugs["cass-operator"]["cassop-330"],
        )
        workqueue.put((operator, bug_id, bug_config))

        # workers write reproduction results
        reproduction_results: Dict[str, bool] = manager.dict()
        # to this dict. Bug ID -> if success
        processes: List[multiprocessing.Process] = []
        for i in range(self._num_workers):
            p = multiprocessing.Process(
                target=run_worker, args=(workqueue, i, reproduction_results)
            )
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        errors = []
        for bug_id, if_reproduced in reproduction_results.items():
            if not if_reproduced:
                errors.append(bug_id)

        self.assertFalse(errors, f"Test failed with {errors}")


if __name__ == "__main__":
    unittest.main()
