import os

import jsonpatch
import yaml

from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_process import PostProcessor


class ChainInputs(PostProcessor):
    """Post processor for extracting inputs from a test run"""

    def __init__(
        self,
        testrun_dir: str,
        config: OperatorConfig,
        ignore_invalid: bool = False,
        acto_namespace: int = 0,
    ):
        self.acto_namespace = acto_namespace
        super().__init__(testrun_dir, config)

        self.all_inputs = []
        for trial in sorted(self.trial_to_steps.keys()):
            steps = self.trial_to_steps[trial].steps
            for i in sorted(steps.keys()):
                step = steps[i]
                if step.run_result.is_invalid_input() and not ignore_invalid:
                    continue
                if step.run_result.oracle_result.is_error():
                    continue
                self.all_inputs.append(
                    {
                        "trial": trial,
                        "gen": step.snapshot.generation,
                        "input": step.snapshot.input_cr,
                        "operator_log": step.snapshot.operator_log,
                        "system_state": step.snapshot.system_state,
                        "cli_output": step.snapshot.cli_result,
                        "runtime_result": step.run_result,
                    }
                )

    def serialize(self, output_dir: str):
        previous_input: dict = {}
        index = 0
        for input_cr in self.all_inputs:
            print(f"{input_cr['trial']}")
            patch = jsonpatch.JsonPatch.from_diff(
                previous_input, input_cr["input"]
            )
            if patch:
                skip_input = False
                for ops in patch:
                    if "/spec/conf" in ops["path"]:
                        print(ops)
                        skip_input = True
                        break

                if skip_input:
                    continue
                with open(
                    os.path.join(output_dir, f"input-{index}.yaml"), "w"
                ) as f:
                    yaml.dump(input_cr["input"], f)
                with open(
                    os.path.join(output_dir, f"input-{index}.patch"), "w"
                ) as f:
                    f.write(str(patch))
                previous_input = input_cr["input"]
                index += 1
