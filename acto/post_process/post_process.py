"""Post process the testrun results"""

import glob
import json
import os
from typing import List

from acto.lib.operator_config import OperatorConfig
from acto.trial import Trial


class PostProcessor:
    """Post processor base class"""

    def __init__(self, testrun_dir: str, config: OperatorConfig):
        # Set config and context
        self.config = config
        context_cache = os.path.join(
            os.path.dirname(config.seed_custom_resource), "context.json"
        )
        with open(context_cache, "r", encoding="utf-8") as context_fin:
            self._context = json.load(context_fin)
            self._context["preload_images"] = set(
                self._context["preload_images"]
            )

        # Initliaze trial dirs
        self._trials: List[str] = []
        # trial_dir -> steps, key by trial_dir string
        self._trial_to_steps: dict[str, Trial] = {}
        trial_dirs = glob.glob(testrun_dir + "/*")
        for trial_dir in trial_dirs:
            if not os.path.isdir(trial_dir):
                continue
            self._trials.append(trial_dir)
            self._trial_to_steps[os.path.basename(trial_dir)] = Trial.load(
                trial_dir
            )

    @property
    def trials(self) -> List[str]:
        """Return trials"""
        return self._trials

    @trials.setter
    def trials(self, value):
        self._trials = value

    @property
    def trial_to_steps(self) -> dict[str, Trial]:
        """Return the dictionary for trial to steps"""
        return self._trial_to_steps

    @property
    def context(self) -> dict:
        """Return context"""
        return self._context
