import logging
from typing import Literal, Optional, Tuple, List, Generator, Protocol, Union, Iterator

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

class TrialInputIteratorLike(Protocol):
    def __iter__(self) -> Generator[Tuple[dict, dict], None, None]:
        pass

    def flush(self):
        pass

    def revert(self):
        pass

    def swap_iterator(self, next_testcase: Iterator[Tuple[List[str], TestCase]]) -> Iterator[
        Tuple[List[str], TestCase]]:
        pass

    @property
    def history(self) -> List[Tuple[dict, dict]]:
        return []


class TrialInputIterator:
    def __init__(self, next_testcase: Iterator[Tuple[List[str], TestCase]], root_schema: ObjectSchema, seed_input: dict):
        self.__next_testcase = next_testcase
        self.__history: List[Tuple[dict, dict]] = []
        self.__queuing_tests: List[Tuple[dict, dict]] = [(seed_input, {'testcase': 'seed', 'field': None})]
        self.__root_schema = root_schema

    def __iter__(self) -> Generator[Tuple[dict, dict], None, None]:
        """
        @return: a tuple of (system_input, signature)
        """
        while True:
            if not self.__queuing_tests:
                # No more tests in the queuing_tests implies that
                # there is no more test cases in the next_testcase
                break

            while self.__queuing_tests:
                # Apply the first test in the queuing_tests
                # and append the result to the history
                # then yield the result
                system_input = self.__queuing_tests.pop(0)
                self.__history.append(system_input)
                yield system_input

            (field_path, testcase) = next(self.__next_testcase, (None, None))
            if (field_path, testcase) == (None, None):
                continue
            signature = testcase.signature(field_path)
            # history[-1] is the last applied system input
            input_with_schema = attach_schema_to_value(self.__history[-1][0], self.__root_schema)
            input_with_schema.create_path(field_path)
            # get the value of the field that we want to mutate and check if it satisfies the precondition
            field_curr_value = input_with_schema.get_value_by_path(field_path)
            if not testcase.test_precondition(field_curr_value):
                # if the precondition is not satisfied, we use setup to make it satisfied
                field_curr_value = testcase.setup(field_curr_value)
                input_with_schema.set_value_by_path(field_curr_value, field_path)
                # and generate the setup test case
                self.__queuing_tests.append((input_with_schema.raw_value(), {**signature, 'testcase': f'{str(testcase)}-setup'}))
            # then mutate the field and generate the test case
            input_with_schema.set_value_by_path(testcase.mutator(field_curr_value), field_path)
            self.__queuing_tests.append((input_with_schema.raw_value(), signature))

    def flush(self):
        """
        Flush the queuing tests
        """
        self.__queuing_tests = []

    def revert(self):
        """
        Revert the last applied test case
        """
        # prevent all the tests in the queuing_tests from being applied
        self.flush()
        # get the faulty test
        faulty_test = self.__history[-1]
        # re-apply the last valid test
        self.__queuing_tests.append((self.__history[-2][0], {'testcase': f'revert-{faulty_test[1]["testcase"]}', 'field': None}))

    def swap_iterator(self, next_testcase: Iterator[Tuple[List[str], TestCase]])->Iterator[Tuple[List[str], TestCase]]:
        next_testcase, self.__next_testcase = next_testcase, self.__next_testcase
        return next_testcase

    @property
    def history(self):
        return self.__history




class Trial:
    def __init__(self, next_input: TrialInputIteratorLike, checker_set: CheckerSet, num_mutation=10):
        self.__next_input = next_input
        self.__checker_set = checker_set
        self.__snapshots: List[Snapshot] = []
        self.__run_results: List[List[OracleResult]] = []
        self.__generation = 0
        self.__num_mutation = num_mutation
        self.__error = None
        # states:
        # normal: the system is normal
        # recovering: the system is recovering from a failed test
        # terminated: the system failed to recover from a failed test
        # runtime_exception: the system encountered a runtime exception
        self.__state: Literal['normal', 'recovering', 'terminated', 'runtime_exception'] = 'normal'
        self.__waiting_for_snapshot = False

    def __iter__(self) -> Generator[dict, None, None]:
        input_iter = iter(self.__next_input)
        while self.__generation <= self.__num_mutation:
            assert self.__waiting_for_snapshot is False

            if self.__state == 'runtime_exception' or self.__state == 'terminated':
                return

            (system_input, testcase_signature) = next(input_iter, (None, None))
            if system_input is None and testcase_signature is None:
                return

            self.__waiting_for_snapshot = True
            yield system_input

    def send_snapshot(self, snapshot: Optional[Snapshot], runtime_error: Optional[Exception]):
        assert self.__waiting_for_snapshot is True
        self.__waiting_for_snapshot = False
        if runtime_error is not None:
            self.__state = 'runtime_exception'
            self.__error = runtime_error
            logging.error(f"Runtime error: {runtime_error}")
            return
        assert snapshot is not None

        self.__snapshots.append(snapshot)
        self.__generation += 1
        self.__waiting_for_snapshot = False
        self.check_snapshot()

    def check_snapshot(self):
        assert self.__state != 'runtime_exception'
        assert self.__state != 'terminated'

        if len(self.__snapshots) < 2:
            # As the seed input will always be valid, we do not need to check it.
            # Therefore, we need at least two snapshots to check.
            return

        prev_snapshot = self.__snapshots[-2]
        snapshot = self.__snapshots[-1]
        result = self.__checker_set.check(snapshot, prev_snapshot)
        self.__run_results.append(result)

        # If all the checkers return ok, we can move on to the next __generation
        if all(map(lambda x: x.means(OracleControlFlow.ok), result)):
            self.__state = 'normal'
            return

        # If any of the checkers return terminate, we terminate the trial
        if any(map(lambda x: x.means(OracleControlFlow.terminate), result)):
            self.__state = 'terminated'
            return

        if any(map(lambda x: x.means(OracleControlFlow.revert), result)):
            # If the result indicates our input is invalid, we need to first run revert to
            # go back to previous system state, then construct a new input without the
            # responsible testcase and re-apply
            if self.__state == 'recovering':
                # if we enter a recovering state twice, we abort the trial
                # because it means we cannot recover from the failure
                self.__state = 'terminated'
            else:
                # if current state is normal, we revert the last applied test case
                self.__state = 'recovering'
                snapshot.set_snapshot_before_applied_input(prev_snapshot)
                self.__next_input.revert()
            return

        if any(map(lambda x: x.means(OracleControlFlow.flush), result)):
            # TODO: What should the behavior be when the oracles mean a flush?
            # See the only checker that will produce a flush
            self.__state = 'normal'
            return

        assert False, "unreachable"

    @property
    def generation(self):
        return self.__generation

    @property
    def state(self):
        return self.__state

    @property
    def error(self):
        return self.__error

    def history_iterator(self) -> Generator[Tuple[Tuple[dict, dict], Union[Exception, Tuple[Snapshot, List[OracleResult]]]], None, None]:
        """
        Return an iterator over the trial history
        The first element of the tuple is a Tuple[dict, dict],
        the first dict is the system input, and the second dict is the test case signature

        The second element of the tuple is a Union[Exception, Tuple[Snapshot, List[OracleResult]]]
        If it is a exception, then it means the runner encountered an exception during the execution,
        and no snapshots can be provided.
        
        If it is a Tuple[Snapshot, List[OracleResult]], 
        the first element of the tuple is the Snapshot,
        and the second element is a list of OracleResult generated by checkers         
        """
        system_input_iter = iter(self.__next_input.history)
        for data in zip(system_input_iter, zip(self.__snapshots, self.__run_results)):
            yield data
        next_system_input = next(system_input_iter, None)
        if next_system_input:
            assert self.__error
            yield next_system_input, self.__error
            assert next(system_input_iter, None) is None
        else:
            assert not self.__error

    def recycle_testcases(self)->Iterator[Tuple[List[str], TestCase]]:
        return self.__next_input.swap_iterator(iter(()))

