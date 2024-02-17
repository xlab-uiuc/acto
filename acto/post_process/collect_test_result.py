import argparse
import glob
import json
import os
import re

import pandas as pd

from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_process import PostProcessor
from acto.result import DifferentialOracleResult


class CollectTestResult(PostProcessor):
    """Post processor for diff test"""

    def __init__(self, testrun_dir: str, config: OperatorConfig):
        super().__init__(testrun_dir, config)

        # Load the post diff test results
        self.diff_test_results: dict[str, DifferentialOracleResult] = {}
        post_diff_test_result_files = glob.glob(
            os.path.join(
                testrun_dir, "post_diff_test", "compare-results-*.json"
            )
        )
        for result_file in post_diff_test_result_files:
            if (
                matches := re.search(r"compare-results-(.*).json", result_file)
            ) is not None:
                input_digest = matches.group(1)
            else:
                raise ValueError(
                    f"Could not parse the input digest from the file name: {result_file}"
                )
            with open(result_file, "r", encoding="utf-8") as file:
                results = json.load(file)
                self.diff_test_results[
                    input_digest
                ] = DifferentialOracleResult.model_validate(results[0])

    def post_process(self, output_path: str):
        """Post process the results"""
        return self.dump_csv(output_path)

    def dump_csv(self, output_path: str):
        """Dump the results to a CSV file"""
        normal_results = []
        for trial in self.trial_to_steps.values():
            for step in trial.steps.values():
                is_alarm = (
                    not step.run_result.is_invalid_input()
                    and step.run_result.oracle_result.is_error()
                )
                normal_results.append(
                    {
                        "Trial number": str(step.run_result.step_id),
                        "Testcase": json.dumps(step.run_result.testcase),
                        "Alarm": is_alarm,
                        "Crash": step.run_result.oracle_result.crash,
                        "Health": step.run_result.oracle_result.health,
                        "Operator log": step.run_result.oracle_result.operator_log,
                        "Consistency": step.run_result.oracle_result.consistency,
                        "Differential": str(
                            step.run_result.oracle_result.differential
                        ),
                        "Custom": step.run_result.oracle_result.custom,
                    }
                )

        for input_digest, result in self.diff_test_results.items():
            normal_results.append(
                {
                    "Trial number": str(result.to_step),
                    "Testcase": input_digest,
                    "Alarm": is_alarm,
                    "Crash": None,
                    "Health": None,
                    "Operator log": None,
                    "Consistency": None,
                    "Differential": str(result),
                    "Custom": None,
                }
            )

        normal_results_df = pd.DataFrame(normal_results)
        normal_results_df = normal_results_df.sort_values(by=["Trial number"])
        normal_results_df.to_csv(output_path, index=False)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect all test results into a CSV file for analysis."
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to the operator config file",
    )
    parser.add_argument(
        "--testrun-dir", type=str, required=True, help="Path to the testrun dir"
    )
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as config_file:
        config = OperatorConfig.model_validate(json.load(config_file))
    post_processor = CollectTestResult(
        args.testrun_dir,
        config,
    )
    post_processor.post_process(os.path.join(args.testrun_dir, "results.csv"))


if __name__ == "__main__":
    main()
