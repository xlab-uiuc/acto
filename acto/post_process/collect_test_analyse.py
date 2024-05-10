import argparse
import glob
import json
import os
import re

from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_process import PostProcessor
from acto.result import DifferentialOracleResult
from pymongo.mongo_client import MongoClient

class CollectTestAnalyse(PostProcessor):

    
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
    
    def add_db_record(self, db_uri: str, record: dict):
        client = MongoClient(db_uri)
        db = client.get_database("acto")
        collection = db["results"]
        
        filter_query = {"operator": record["operator"]}
        collection.update_one(filter_query, {"$set": record}, upsert=True)
        client.close()
        
    def post_process(self, operator_name: str, db_uri: str):
        """Post process the results"""
        
        total_trial = 0
        alarm_cnt = 0
        crash_cnt = 0
        health_cnt = 0
        testcases = dict()
        fields = dict()
        
        for trial in self.trial_to_steps.values():
            for step in trial.steps.values():
                total_trial += 1
                is_alarm = (
                    not step.run_result.is_invalid_input()
                    and step.run_result.oracle_result.is_error()
                )
                if is_alarm:
                    alarm_cnt += 1
                    testcase = step.run_result.testcase
                    casename = testcase["testcase"]
                    if casename not in testcases:
                        testcases[casename] = 1
                    else:
                        testcases[casename] = testcases[casename] + 1
                    
                    field = json.loads(testcase["field"])
                    if field[-1] == "ACTOKEY":
                        fieldname = field[-2]
                    else:
                        fieldname = field[-1]
                    if fieldname not in fields:
                        fields[fieldname] = 1
                    else:
                        fields[fieldname] = fields[fieldname] + 1
                if step.run_result.oracle_result.crash:
                    crash_cnt += 1
                if step.run_result.oracle_result.health:
                    health_cnt += 1
                
        for input_digest, result in self.diff_test_results.items():
            total_trial += 1
            alarm_cnt += 1
        
        record = {
            "operator": operator_name,
            "trial": total_trial,
            "alarm": alarm_cnt,
            "crash": crash_cnt,
            "health": health_cnt,
            "cases": testcases,
            "fields": fields
        }
        self.add_db_record(db_uri, record)
        

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
        "--db_uri",type=str, required=True, help="Connect uri to MongoDB", default="mongodb://localhost:27017/"
    )
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as config_file:
        config = OperatorConfig.model_validate(json.load(config_file))
    post_processor = CollectTestAnalyse(
        args.testrun_dir,
        config,
    )
    operator_name = args.config.split("/")[1]
    post_processor.post_process(operator_name, args.db_uri)


if __name__ == "__main__":
    main()
