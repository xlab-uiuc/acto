import logging
from collections.abc import Iterator
from typing import Literal, Optional, Tuple, List, Generator, Protocol

from acto.checker.checker import OracleControlFlow, OracleResult
from acto.checker.checker_set import CheckerSet
from acto.input import TestCase
from acto.input.value_with_schema import attach_schema_to_value
from acto.schema import ObjectSchema


class Snapshot(Protocol):
    def set_snapshot_before_applied_input(self, snapshot: 'Snapshot'):
        pass

    def save(self, dir_path: str):
        pass


class TrialInputIterator:
    def __init__(self, next_testcase: Iterator[Tuple[List[str], TestCase]], root_schema: ObjectSchema, seed_input: dict):
        self.next_testcase = next_testcase
        self.history = []
        self.queuing_tests: List[Tuple[dict, dict]] = [(seed_input, {'testcase': 'seed', 'field': None})]
        self.root_schema = root_schema

    def __iter__(self) -> Generator[Tuple[dict, dict], None, None]:
        """
        @return: a tuple of (system_input, signature)
        """
        while True:
            if not self.queuing_tests:
                # No more tests in the queuing_tests implies that
                # there is no more test cases in the next_testcase
                break

            while self.queuing_tests:
                # Apply the first test in the queuing_tests
                # and append the result to the history
                # then yield the result
                system_input = self.queuing_tests.pop(0)
                self.history.append(system_input)
                yield system_input

            (field_path, testcase) = next(self.next_testcase, (None, None))
            if (field_path, testcase) == (None, None):
                continue
            signature = testcase.signature(field_path)
            # history[-1] is the last applied system input
            input_with_schema = attach_schema_to_value(self.history[-1][0], self.root_schema)
            input_with_schema.create_path(field_path)
            # get the value of the field that we want to mutate and check if it satisfies the precondition
            field_curr_value = input_with_schema.get_value_by_path(field_path)
            if not testcase.test_precondition(field_curr_value):
                # if the precondition is not satisfied, we use setup to make it satisfied
                field_curr_value = testcase.setup(field_curr_value)
                input_with_schema.set_value_by_path(field_curr_value, field_path)
                # and generate the setup test case
                self.queuing_tests.append((input_with_schema.raw_value(), {**signature, 'testcase': f'{str(testcase)}-setup'}))
            # then mutate the field and generate the test case
            input_with_schema.set_value_by_path(testcase.mutator(field_curr_value), field_path)
            self.queuing_tests.append((input_with_schema.raw_value(), signature))

    def flush(self):
        """
        Flush the queuing tests
        """
        self.queuing_tests = []

    def revert(self):
        """
        Revert the last applied test case
        """
        # prevent all the tests in the queuing_tests from being applied
        self.flush()
        # pop the faulty test
        self.history.pop()
        # re-apply the last valid test
        self.queuing_tests.append(self.history.pop())


class Trial:
    def __init__(self, next_input: TrialInputIterator, checker_set: CheckerSet, num_mutation=10):
        self.next_input = next_input
        self.checker_set = checker_set
        self.snapshots: List[Snapshot] = []
        self.run_results: List[List[OracleResult]] = []
        self.generation = 0
        self.num_mutation = num_mutation
        self.error = None
        # states:
        # normal: the system is normal
        # recovering: the system is recovering from a failed test
        # terminated: the system failed to recover from a failed test
        # runtime_exception: the system encountered a runtime exception
        self.state: Literal['normal', 'recovering', 'terminated', 'runtime_exception'] = 'normal'
        self.waiting_for_snapshot = False

    def __iter__(self) -> Generator[dict, None, None]:
        input_iter = iter(self.next_input)
        while self.generation <= self.num_mutation:
            assert self.waiting_for_snapshot is False

            if self.state == 'runtime_exception' or self.state == 'terminated':
                return

            (system_input, testcase_signature) = next(input_iter, (None, None))
            if system_input is None and testcase_signature is None:
                return

            self.waiting_for_snapshot = True
            yield system_input

    def send_snapshot(self, snapshot: Optional[Snapshot], runtime_error: Optional[Exception]):
        assert self.waiting_for_snapshot is True
        self.waiting_for_snapshot = False
        if runtime_error is not None:
            self.state = 'runtime_exception'
            self.error = runtime_error
            logging.error(f"Runtime error: {runtime_error}")
            return
        assert snapshot is not None

        self.snapshots.append(snapshot)
        self.generation += 1
        self.waiting_for_snapshot = False
        self.check_snapshot()

    def check_snapshot(self):
        assert self.state != 'runtime_exception'
        assert self.state != 'terminated'

        if len(self.snapshots) < 2:
            # As the seed input will always be valid, we do not need to check it.
            # Therefore, we need at least two snapshots to check.
            return

        prev_snapshot = self.snapshots[-2]
        snapshot = self.snapshots[-1]
        result = self.checker_set.check(snapshot, prev_snapshot)
        self.run_results.append(result)

        # If all the checkers return ok, we can move on to the next generation
        if all(map(lambda x: x.means(OracleControlFlow.ok), result)):
            self.state = 'normal'
            return

        # If any of the checkers return terminate, we terminate the trial
        if any(map(lambda x: x.means(OracleControlFlow.terminate), result)):
            self.state = 'terminated'
            return

        if any(map(lambda x: x.means(OracleControlFlow.revert), result)):
            # If the result indicates our input is invalid, we need to first run revert to
            # go back to previous system state, then construct a new input without the
            # responsible testcase and re-apply
            if self.state == 'recovering':
                # if we enter a recovering state twice, we abort the trial
                # because it means we cannot recover from the failure
                self.state = 'terminated'
            else:
                # if current state is normal, we revert the last applied test case
                self.state = 'recovering'
                snapshot.set_snapshot_before_applied_input(prev_snapshot)
                self.next_input.revert()
            return

        if any(map(lambda x: x.means(OracleControlFlow.flush), result)):
            if self.state == 'recovering':
                # TODO: what if we encounter a flush when we are recovering?
                self.state = 'terminated'
            else:
                self.next_input.flush()
            return

        assert False, "unreachable"
