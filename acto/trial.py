import os

import pydantic
from typing_extensions import Self

from acto.result import RunResult
from acto.snapshot import Snapshot, input_cr_path


class Step(pydantic.BaseModel):
    """A step containing the Snapshot and the Runtime Result"""

    snapshot: Snapshot
    run_result: RunResult

    @classmethod
    def load(cls, trial_dir: str, generation: int) -> Self:
        """Load a step from the given trial directory and generation"""
        snapshot = Snapshot.load(trial_dir, generation)
        run_result = RunResult.load(trial_dir, generation)
        return cls(snapshot=snapshot, run_result=run_result)


class Trial(pydantic.BaseModel):
    """A trial containing a list of Steps"""

    steps: dict[str, Step]

    @classmethod
    def load(cls, trial_dir: str) -> Self:
        """Load a trial from the given trial directory"""
        steps = {}
        for gen in range(0, 1000):
            if not os.path.exists(input_cr_path(trial_dir, gen)):
                break
            try:
                steps[str(gen)] = Step.load(trial_dir, gen)
            except FileNotFoundError:
                continue
        return cls(steps=steps)
