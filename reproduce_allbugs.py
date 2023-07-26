from enum import Enum
from tabulate import tabulate
from acto.reproduce import reproduce, reproduce_postdiff
from test.utils import BugConfig, all_bugs

class BugCateogry(str, Enum):
    UNDESIRED_STATE = 'undesired_state'
    SYSTEM_ERROR = 'system_error'
    OPERATOR_ERROR = 'operator_error'
    RECOVERY_FAILURE = 'recovery_failure'

    def __str__(self) -> str:
        return self.value


if __name__ == '__main__':
    reproduce_results = {}
    failed_reproductions = {}

    for operator, bugs in all_bugs.items():
        operator_config = f'data/{operator}/config.json'
        reproduce_results[operator] = {
            BugCateogry.UNDESIRED_STATE: 0,
            BugCateogry.SYSTEM_ERROR: 0,
            BugCateogry.OPERATOR_ERROR: 0,
            BugCateogry.RECOVERY_FAILURE: 0,
        }
        for bug_id, bug_config in bugs.items():
            repro_dir = bug_config.dir
            work_dir = f'testrun-{bug_id}'

            if bug_config.difftest:
                reproduce(work_dir, repro_dir, operator_config, cluster_runtime='KIND')
                if reproduce_postdiff(work_dir, operator_config, cluster_runtime='KIND'):
                    print(f"Bug {bug_id} reproduced!")
                    reproduce_results[operator][bug_config.category] += 1
                    continue
                else:
                    print(f"Bug {bug_id} not reproduced!")
                    failed_reproductions[bug_id] = True
                    continue
            else:
                if reproduce(work_dir, repro_dir, operator_config, cluster_runtime='KIND'):
                    print(f"Bug {bug_id} reproduced!")
                    reproduce_results[operator][bug_config.category] += 1
                    continue
                else:
                    print(f"Bug {bug_id} not reproduced!")
                    failed_reproductions[bug_id] = True
                    continue

    table = []
    for operator, reproduce_result in reproduce_results.items():
        table.append([operator, reproduce_result[BugCateogry.UNDESIRED_STATE], reproduce_result[BugCateogry.SYSTEM_ERROR], reproduce_result[BugCateogry.OPERATOR_ERROR], reproduce_result[BugCateogry.RECOVERY_FAILURE]])

    print(tabulate(table, headers=['Operator', 'Undesired State', 'System Error', 'Operator Error', 'Recovery Failure']))