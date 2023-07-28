import argparse
import json
import re

from tabulate import tabulate

from test.utils import operator_pretty_name_mapping

operator_campaigns = {
    'cass-operator': 'testrun-cass',
    'cockroach-operator': 'testrun-crdb',
    'knative-operator-eventing': 'testrun-knative-eventing',
    'knative-operator-serving': 'testrun-knative-serving',
    'mongodb-community-operator': 'testrun-mongodb-comm',
    'percona-server-mongodb-operator': 'testrun-percona-mongodb',
    'percona-xtradb-cluster-operator': 'testrun-xtradb',
    'rabbitmq-operator': 'testrun-rabbitmq',
    'redis-operator': 'testrun-redis',
    'redis-ot-container-kit-operator': 'testrun-redis-ot',
    'tidb-operator': 'testrun-tidb',
    'zookeeper-operator': 'testrun-zk',
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="campaign-data", required=False)
    args = parser.parse_args()

    num_ops_table = {}
    for operator, campaign_dir in operator_campaigns.items():
        test_plan_dir = f"{args.input}/{campaign_dir}/test_plan.json"
        testrun_info = f"{args.input}/{campaign_dir}/testrun_info.json"
        difftest_dir = f"{args.input}/{campaign_dir}/post_diff_test"
        total_ops = 0

        with open(test_plan_dir, 'r') as test_plan_f, open(testrun_info, 'r') as testrun_info_f:
            test_plan = json.load(test_plan_f)
            testrun_info = json.load(testrun_info_f)

            num_ops_based_on_test_plan = 0
            num_ops_based_on_testrun_info = 0
            groups = test_plan['normal_subgroups']
            for group in groups:
                num_ops_based_on_test_plan += len(group)

            num_ops_based_on_testrun_info = testrun_info['num_total_testcases'][
                'num_semantic_testcases'] + testrun_info['num_total_testcases'][
                    'num_normal_testcases']
            
            assert(num_ops_based_on_test_plan == num_ops_based_on_testrun_info)
            total_ops += num_ops_based_on_testrun_info

        with open(difftest_dir + "/test.log", 'r') as diff_test_info_f:
            for line in diff_test_info_f:
                match = re.search(r"Found ([0-9]+) unique inputs", line)
                if match:
                    total_diff_ops = int(match.group(1))
                    break

        total_ops += total_diff_ops

        num_ops_table[operator] = total_ops

    num_ops_table['knative-operator'] = num_ops_table['knative-operator-eventing'] + num_ops_table['knative-operator-serving']
    del num_ops_table['knative-operator-eventing']
    del num_ops_table['knative-operator-serving']

    table_8 = []
    for operator, num_ops in num_ops_table.items():
        table_8.append([operator_pretty_name_mapping[operator], num_ops])

    table_8 = sorted(table_8, key=lambda status: status[0])
    print(tabulate(table_8, headers=['Operator', '# Operations']))


