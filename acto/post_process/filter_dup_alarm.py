import argparse
import json
import pydantic
import yaml
import sys
import re
import os
import pandas as pd

from typing import Optional, List, Any

from acto.post_process.post_process import PostProcessor
from acto.lib.operator_config import OperatorConfig
from acto.utils.thread_logger import get_thread_logger
from acto.common import Diff
from acto.result import ConsistencyOracleResult

logger = get_thread_logger(with_prefix=False)


class Bug(pydantic.BaseModel):
    """
    Class for resolving user-defined deduplicate alarm config file
    """
    name: Optional[str] = pydantic.Field(description="Name of the bug")
    properties: List[Any] = pydantic.Field(
        description="Regex patterns for properties to consider in deduplication"
    )
    prev: Any = pydantic.Field(description="Previous value")
    curr: Any = pydantic.Field(description="Current value")

    @classmethod
    def load(cls, file_path: str) -> "Bug":
        """
        deserialize Bug object from filter file
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)['bug']
                return cls(**yaml_data)
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {e}")


class FilterTestResult(PostProcessor):
    def __init__(self, testrun_dir: str, config: OperatorConfig):
        super().__init__(testrun_dir, config)

    def post_process(self, filter_file: str, output_path: str):
        bug = Bug.load(filter_file)
        self.filter_by_fields(bug, output_path)

    def compare(self, bug: Bug, diff: Diff) -> bool:
        """Compare Bug properties with Diff path and prev/curr values"""
        # convert Diff.path to string to compare
        diff_path = '.'.join(map(str, diff.path.path))
        # check prev and curr variable type
        if type(bug.prev) != type(diff.prev) or type(bug.curr) != type(diff.curr):
            return False
        # check the properties match
        if re.match(str(bug.prev), str(diff.prev)) and re.match(str(bug.curr), str(diff.curr)):
            for pattern in bug.properties:
                if re.search(pattern, diff_path):
                    return True
        return False

    def filter_by_fields(self, bug: Bug, output_path: str):
        duplicate_alarms = []
        for trial in self.trial_to_steps.values():
            for step in trial.steps.values():
                # extract the input diff for each step
                consistency_result = step.run_result.oracle_result.consistency
                if not isinstance(consistency_result, ConsistencyOracleResult):
                    continue
                # use regex to compare input_diff with the user-defined bug
                input_diff = consistency_result.input_diff
                if not self.compare(bug, input_diff):
                    continue
                # dump csv for duplicate alarms, maybe replace with change the self.trail_to_steps and then use dump_csv
                is_alarm = (
                        not step.run_result.is_invalid_input()
                        and step.run_result.oracle_result.is_error()
                )
                duplicate_alarms.append(
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
        duplicate_results_df = pd.DataFrame(duplicate_alarms)
        if len(duplicate_results_df) != 0:
            duplicate_results_df = duplicate_results_df.sort_values(by=["Trial number"])
        duplicate_results_df.to_csv(output_path, index=False)


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
    parser.add_argument(
        "--filter", type=str, required=True, help="Path to the results filter file"
    )
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as config_file:
        config = OperatorConfig.model_validate(json.load(config_file))
    post_processor = FilterTestResult(
        args.testrun_dir,
        config
    )
    post_processor.post_process(args.filter, os.path.join(args.testrun_dir, "dup_results.csv"))


if __name__ == "__main__":
    main()
