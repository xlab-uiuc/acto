"""Post process the testrun results"""
import glob
import json
import os
from typing import List

from acto.lib.operator_config import OperatorConfig
from acto.trial import Trial

# class Step:
#     """A step in a trial

#     Attributes:
#         input (Dict): input to the operator
#         operator_log (str): operator log
#         system_state (Dict): system state
#         cli_output (str): cli output
#         runtime_result (Dict): runtime result
#     """

#     def __init__(
#         self,
#         trial_dir: str,
#         gen: int,
#         input_cr: Dict,
#         operator_log: list[str],
#         system_state: Dict,
#         cli_output: str,
#         runtime_result: Dict,
#     ):
#         self._trial_dir = trial_dir
#         self._gen = gen
#         self._input = input_cr
#         self._input_digest = hashlib.md5(
#             json.dumps(input_cr, sort_keys=True).encode("utf-8")
#         ).hexdigest()
#         self._operator_log = operator_log
#         self._system_state = system_state
#         self._cli_output = cli_output
#         self._runtime_result = RunResult(**runtime_result)

#     @property
#     def trial_dir(self) -> str:
#         """Return trial directory"""
#         return self._trial_dir

#     @property
#     def gen(self) -> int:
#         """Return generation"""
#         return self._gen

#     @property
#     def input(self) -> Dict:
#         """Return input"""
#         return self._input

#     @property
#     def input_digest(self) -> str:
#         """Return input digest"""
#         return self._input_digest

#     @property
#     def operator_log(self) -> list[str]:
#         """Return operator log"""
#         return self._operator_log

#     @property
#     def system_state(self) -> Dict:
#         """Return system state"""
#         return self._system_state

#     @property
#     def cli_output(self) -> str:
#         """Return cli output"""
#         return self._cli_output

#     @property
#     def runtime_result(self) -> RunResult:
#         """Return runtime result"""
#         return self._runtime_result


# def read_trial_dir(trial_dir: str) -> Dict[str, Step]:
#     """Read a trial directory and return a list of steps"""

#     steps: Dict[str, Step] = {}
#     for generation in range(0, 20):
#         if not os.path.exists(f"{trial_dir}/mutated-{generation:03d}.yaml"):
#             break

#         step = construct_step(trial_dir, generation)
#         if step is None:
#             continue
#         else:
#             steps[str(generation)] = step

#     return steps


# def construct_step(trial_dir, generation) -> Optional[Step]:
#     """Construct a step from a trial directory and generation"""
#     events_log_path = f"{trial_dir}/events-{generation:03d}.json"
#     mutated_filename = f"{trial_dir}/mutated-{generation:03d}.yaml"
#     operator_log_path = f"{trial_dir}/operator-{generation:03d}.log"
#     system_state_path = f"{trial_dir}/system-state-{generation:03d}.json"
#     cli_output_path = f"{trial_dir}/cli-output-{generation:03d}.log"
#     runtime_result_path = (
#         f"{trial_dir}/generation-{generation:03d}-runtime.json"
#     )

#     if not os.path.exists(operator_log_path):
#         return None

#     if not os.path.exists(runtime_result_path):
#         return None

#     with open(mutated_filename, "r", encoding="utf-8") as input_file, open(
#         operator_log_path,
#         "r",
#         encoding="utf-8",
#     ) as operator_log_file, open(
#         system_state_path,
#         "r",
#         encoding="utf-8",
#     ) as system_state_file, open(
#         events_log_path,
#         "r",
#         encoding="utf-8",
#     ) as _, open(
#         cli_output_path,
#         "r",
#         encoding="utf-8",
#     ) as cli_output, open(
#         runtime_result_path,
#         "r",
#         encoding="utf-8",
#     ) as runtime_result_file:
#         input_cr = yaml.load(input_file, Loader=yaml.FullLoader)
#         operator_log = operator_log_file.read().splitlines()
#         system_state = json.load(system_state_file)
#         cli_result = json.load(cli_output)
#         runtime_result = json.load(runtime_result_file)

#         return Step(
#             trial_dir,
#             generation,
#             input_cr,
#             operator_log,
#             system_state,
#             cli_result,
#             runtime_result,
#         )


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
        self._trial_to_steps: dict[
            str, Trial
        ] = {}  # trial_dir -> steps, key by trial_dir string
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
