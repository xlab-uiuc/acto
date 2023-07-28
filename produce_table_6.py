from tabulate import tabulate
from test.utils import BugConfig, all_bugs, BugConsequence

consequence_table = {
    BugConsequence.SYSTEM_FAILURE: 0,
    BugConsequence.RELIABILITY_ISSUE: 0,
    BugConsequence.SECURITY_ISSUE: 0,
    BugConsequence.RESOURCE_ISSUE: 0,
    BugConsequence.OPERATION_OUTAGE: 0,
    BugConsequence.MISCONFIGURATION: 0,
}

for operator, bugs in all_bugs.items():
    for bug_id, bug_config in bugs.items():
        consequences = bug_config.consequences
        for consequence in consequences:
            consequence_table[consequence] += 1

table_6 = []
for consequence, count in consequence_table.items():
    table_6.append([consequence, count])

print(tabulate(table_6, headers=['Consequence', '# Bugs']))