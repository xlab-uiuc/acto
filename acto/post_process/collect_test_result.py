import argparse
import json

import pandas as pd

from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_process import PostProcessor


class CollectTestResult(PostProcessor):
    """Post processor for diff test"""

    def post_process(self, output_path: str):
        """Post process the results"""
        return self.dump_csv(output_path)

    def dump_csv(self, output_path: str):
        """Dump the results to a CSV file"""
        normal_results = []
        for trial in self.trial_to_steps.values():
            for step in trial.steps.values():
                normal_results.append(
                    {
                        "Trial number": str(step.run_result.step_id),
                        "Testcase": json.dumps(step.run_result.testcase),
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

        normal_results_df = pd.DataFrame(normal_results)
        normal_results_df = normal_results_df.sort_values(by=["Trial number"])
        normal_results_df.to_csv(output_path, index=False)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--testrun-dir", type=str, required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as config_file:
        config = OperatorConfig.model_validate(json.load(config_file))
    post_processor = CollectTestResult(
        args.testrun_dir,
        config,
    )
    post_processor.post_process("./result.csv")


if __name__ == "__main__":
    main()
