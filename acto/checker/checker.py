from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import auto
from functools import wraps
from typing import Callable, Optional, Union

from strenum import StrEnum

from acto.snapshot import Snapshot


class OracleControlFlow(StrEnum):
    ok = auto()
    flush = auto()
    revert = auto()
    terminate = auto()
    redo = auto()


def means_first(condition: Callable[['Checker'], bool]):
    def decorator(function):
        @wraps(function)
        def wrapper(*args):
            self = args[0]
            if condition(self):
                return function(*args)
            return False

        return wrapper

    return decorator


@dataclass
class OracleResult(Exception):
    message: str = OracleControlFlow.ok
    exception: Optional[Exception] = None
    emit_by: str = '<None>'
    time_to_wait_until_next_step: int | float = 0

    def means(self, control_flow: Union[OracleControlFlow, str]):
        method_name = f'means_{control_flow.name}'
        return getattr(self, method_name)()

    def set_emitter(self, oracle: 'Checker'):
        self.emit_by = oracle.name

    @means_first(lambda self: not self.means_terminate())
    def means_ok(self):
        return self.message == OracleControlFlow.ok

    @staticmethod
    def means_flush():
        return False

    @means_first(lambda self: not self.means_terminate())
    def means_revert(self):
        return self.message != OracleControlFlow.ok

    def means_terminate(self):
        return self.exception is not None

    @staticmethod
    def means_redo():
        return False

    def all_meanings(self):
        return [meaning for meaning in OracleControlFlow if self.means(meaning)]


class Checker(ABC):

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError

    def __init__(self, **kwargs):
        pass

    def check(self, snapshot: Snapshot) -> Optional[OracleResult]:
        if not self.enabled(snapshot):
            return None
        try:
            result = self._check(snapshot)
        except Exception as e:
            result = OracleResult(message=str(e), exception=e)
        result.set_emitter(self)
        return result

    @staticmethod
    def enabled(snapshot: Snapshot) -> bool:
        return True

    @abstractmethod
    def _check(self, snapshot: Snapshot) -> OracleResult:
        raise NotImplementedError


class UnaryChecker(Checker, ABC):
    def _check(self, snapshot: Snapshot) -> OracleResult:
        return self._unary_check(snapshot)

    @abstractmethod
    def _unary_check(self, snapshot: Snapshot) -> OracleResult:
        pass


class BinaryChecker(Checker, ABC):
    @staticmethod
    def enabled(snapshot: Snapshot) -> bool:
        return snapshot.parent is not None

    def _check(self, snapshot: Snapshot) -> OracleResult:
        return self._binary_check(snapshot, snapshot.parent)

    @abstractmethod
    def _binary_check(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        pass
