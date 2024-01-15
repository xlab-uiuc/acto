"""Checker interface"""
from abc import ABC, abstractmethod
from typing import Optional

from acto.result import OracleResult
from acto.snapshot import Snapshot


class CheckerInterface(ABC):
    """Interface for checkers"""

    def __init__(self):
        pass

    @abstractmethod
    def check(
        self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot
    ) -> Optional[OracleResult]:
        """Check the given step and return the result of the check"""
        raise NotImplementedError()
