from abc import ABC, abstractmethod

from acto.common import OracleResult
from acto.snapshot import Snapshot


class Checker(ABC):

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError

    def __init__(self, trial_dir: str, **kwargs):
        self.trial_dir = trial_dir

    @abstractmethod
    def check(self, generation: int, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        raise NotImplementedError()
