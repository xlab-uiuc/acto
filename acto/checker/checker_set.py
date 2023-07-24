from typing import List

from acto.checker.checker import OracleResult
from acto.checker.impl.crash import CrashChecker
from acto.checker.impl.health import HealthChecker
from acto.checker.impl.kubectl_cli import KubectlCliChecker
from acto.checker.impl.operator_log import OperatorLogChecker
from acto.checker.impl.recovery import RecoveryChecker
from acto.checker.impl.state import StateChecker
from acto.input import InputModel
from acto.snapshot import Snapshot

default_checker_generators = [CrashChecker, HealthChecker, KubectlCliChecker, OperatorLogChecker, StateChecker, RecoveryChecker]


class CheckerSet:
    def __init__(self, context: dict, input_model: InputModel, checker_generators: list = None):
        if checker_generators is None:
            checker_generators = default_checker_generators
        self.context = context
        self.input_model = input_model

        checker_args = {
            'input_model': self.input_model,
            'context': self.context
        }
        self.checkers = [checkerGenerator(**checker_args) for checkerGenerator in checker_generators]

    def check(self, snapshot: Snapshot) -> List[OracleResult]:
        return list(filter(lambda r: r is not None, map(lambda checker: checker.check(snapshot), self.checkers)))

# If we want to decouple the checkers from the Snapshot structure, we can use the following code:
#
# from typing import Protocol
# class Snapshot(Protocol):
#     system_state: dict
#     other_attributes_needed ...
#     def __some_method__(self):
#         pass
