### Alarms analysis


1, 2, 3. `testrun-2024-02-23-20-31/trial-02-0007/0001`, `testrun-2024-02-23-20-31/trial-02-0006/0004`, `testrun-2024-02-23-20-31/trial-02-0008/0001`

Testcase: `{"field": "[\"spec\", \"affinity\", \"nodeLabels\", \"ACTOKEY\"]", "testcase": "string-change"}`

Acto changes the nodeLabels field from "NotPresent" to "ACTOKEY". 

`message='statefulset: test-cluster-postgresql replicas [1] ready_replicas [None]\npod: test-cluster-postgresql-0'`

The health oracle expects that there should be 1 ready replica in the system, but there are none, so it raises an alarm.

The following event occurs: `0/4 nodes are available: 1 node(s) didn't match Pod's node affinity/selector. preemption: 0/4 nodes are available: 1 Preemption is not helpful for scheduling, 3 No preemption victims found for incoming pod.`

Basically "ACTOKEY" is not a valid node label. However, the operator shuts down the running replica itself instead of rejecting the invalid state (which results in updating the affinity rule with an incorrect value). Thus the alarm is a **misoperation**.


4, 5. `testrun-2024-02-23-20-31/trial-02-0013/0005`, `testrun-2024-02-23-20-31/trial-03-0007/0003`

Testcase: `{"field": "[\"spec\", \"componentSpecs\", 0, \"services\", 0, \"annotations\", \"ACTOKEY\"]", "testcase": "string-deletion"}`

Acto removes spec.componentSpecs[0].services[0].annotations. Previously it was "ACTOKEY".
The consistency oracle raises an alarm that there is no such matching system change.

message='Found no matching fields for input' input_diff=Diff(prev='ACTOKEY', curr='', path=["spec", "componentSpecs", 0, "services", 0, "annotations", "ACTOKEY"]) system_state_diff=None

This occurs because the Reconcile() function of the operator calls ApplyParameters(), which calls DoMerge() in reconfigure_pipeline.go that merges operator configurations. 
After several steps this calls MergeMap() on the annotations, that merges the backup annotation with the new one. So the old annotation value is not deleted. So this is a **true** alarm.