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

6-10. `testrun-2024-02-23-20-31/trial-00-0019/0001, testrun-2024-02-23-20-31/trial-00-0021/0001, testrun-2024-02-23-20-31/trial-03-0014/0001,
testrun-2024-02-23-20-31/trial-04-0019/0001`

In these alarms acto adds some variation of:
```
    userResourceRefs:
      configMapRefs:
      - asVolumeFrom:
        - ACTOKEY
        configMap: {}
        mountPoint: /jiyyay4e9mdlz06j2mn3n22xn2zcuuqautlbyltm6cyh67ynqwi03nwqmgi-18wpxd-cq7ixsypzbe3b-0blkusvc-dflm59kq0n50awotvkpxkddcs2f5bwjyskqqrm13taiestlhg4rkg1kh2pihr8a1f7yys3fauo4-m4ftdy6bmy6gg3ybr7us448uco7l50z-1m1q54wy2c9avdd-unnfqx12zrge
        name: e
```

Normal kubeblocks deployment runs fine.
However in each of these cases, configMap.name is not present so an error like
`spec.volumes[3].configMap.name: Required value` is generated in the postgresql pod.

This is a **misconfiguration** since the generated yaml is incorrect.

11. `testrun-2024-02-23-20-31/trial-03-0015/0001`

Similar to above, but here the spec.volumes[3].name field contains dots, which is not allowed.

**Misconfiguration**

12. `testrun-2024-02-23-20-31/trial-07-0007/0001`, `testrun-2024-02-23-20-31/trial-01-0017/0001`, `testrun-2024-02-23-20-31/trial-01-0016/0001`, `testrun-2024-02-23-20-31/trial-01-0018/0001`, 

Same as 6-10

13. `testrun-2024-02-23-20-31/trial-07-0009/0003`

Similar to above. `configMapsRef.name` yaml should not contain dots. **Misconfiguration**

14 - 22. `testrun-2024-02-23-20-31/trial-02-0021/0001`, `testrun-2024-02-23-20-31/trial-02-0020/0009`, `testrun-2024-02-23-20-31/trial-03-0017/0001`, `testrun-2024-02-23-20-31/trial-05-0002/0001`, `testrun-2024-02-23-20-31/trial-05-0001/0001`, `testrun-2024-02-23-20-31/trial-05-0000/0001`, `testrun-2024-02-23-20-31/trial-05-0000/0001`, `testrun-2024-02-23-20-31/trial-05-0000/0001`, `testrun-2024-02-23-20-31/trial-08-0000/0003`

Similar to 6-10, secret.secretName not specified in generated yaml, making it invalid
`error: Pod "pg-cluster-postgresql-0" is invalid: spec.volumes[3].secret.secretName: Required value`

**Misconfiguration**

23 - 26. `testrun-2024-02-23-20-31/trial-00-0006/0006`, `testrun-2024-02-23-20-31/trial-05-0014/0001`, `testrun-2024-02-23-20-31/trial-05-0013/0002`, `testrun-2024-02-23-20-31/trial-05-0015/0001`

```0/4 nodes are available: 1 node(s) didn't match Pod's node affinity/selector. preemption: 0/4 nodes are available: 1 Preemption is not helpful for scheduling, 3 No preemption victims found for incoming pod..
```

Acto adds a single node label to the yaml in the affinity rules, that does not match the correct label for the node. 
All the cases follow similar pattern.
**Misoperation**

27 - 30. `testrun-2024-02-23-20-31/trial-06-0004/0001`, `testrun-2024-02-23-20-31/trial-07-0004/0002`, `testrun-2024-02-23-20-31/trial-04-0015/0002`, `testrun-2024-02-23-20-31/trial-04-0016/0003`

```...Invalid value: "": name part must consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyName',  or 'my.name',  or '123-abc', regex used for validation is '([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]'), spec.topologySpreadConstraints[0].topologyKey: Required value: can not be empty
```
Invalid yaml generated. Acto sets topologyKeys to ''.

**Misoperation**


31 - 38. `testrun-2024-02-23-20-31/trial-04-0014/0005`, `testrun-2024-02-23-20-31/trial-08-0006/0002`, `testrun-2024-02-23-20-31/trial-00-0009/0001`, `testrun-2024-02-23-20-31/trial-08-0007/0002`, `testrun-2024-02-23-20-31/trial-03-0013/0001`, `testrun-2024-02-23-20-31/trial-05-0021/0002`, `testrun-2024-02-23-20-31/trial-06-0011/0001`, `testrun-2024-02-23-20-31/trial-05-0022/0002`

```Pod "pg-cluster-postgresql-0" is invalid: [spec.tolerations[0].effect: Invalid value: "INVALID_EFFECT": effect must be 'NoExecute' when `tolerationSeconds` is set, spec.tolerations[0].effect: Unsupported value: "INVALID_EFFECT": supported values: "NoSchedule", "PreferNoSchedule", "NoExecute"```

Acto incorrectly sets the yaml for tolerations. Similar errors for each case.
**Misoperation**

39 - 40. `testrun-2024-02-23-20-31/trial-04-0005/0001`, `testrun-2024-02-23-20-31/trial-05-0020/0006`

Same as 23-26 **Misoperation**

41 - 44. `testrun-2024-02-23-20-31/trial-07-0001/0001`, `testrun-2024-02-23-20-31/trial-07-0000/0004`, `testrun-2024-02-23-20-31/trial-07-0014/0001`, `testrun-2024-02-23-20-31/trial-02-0009/0001`

```create Pod pg-cluster-postgresql-0 in StatefulSet pg-cluster-postgresql failed error: Pod "pg-cluster-postgresql-0" is invalid: [spec.containers[0].resources.requests[ACTOKEY]: Invalid value: "ACTOKEY": must be a standard resource type or fully qualified, spec.containers[0].resources.requests[ACTOKEY]: Invalid value: "ACTOKEY": must be a standard resource for containers]```

Acto specifies an invalid value in the resources yaml. All cases have similar errors.

**Misoperation**

45 - 47. `testrun-2024-02-23-20-31/trial-06-0006/0004`, `testrun-2024-02-23-20-31/trial-00-0000/0008`, `testrun-2024-02-23-20-31/trial-07-0010/0009`

Invalid yaml configuration, similar to previous cases

**Misoperation**

48 - 60. `testrun-2024-02-23-20-31/trial-00-0005/0002`, `testrun-2024-02-23-20-31/trial-00-0004/0002`, `testrun-2024-02-23-20-31/trial-06-0012/0006`, `testrun-2024-02-23-20-31/trial-06-0013/0003`, `testrun-2024-02-23-20-31/trial-05-0006/0006`, `testrun-2024-02-23-20-31/trial-05-0007/0003`, `testrun-2024-02-23-20-31/trial-00-0002/0002`, `testrun-2024-02-23-20-31/trial-00-0001/0002`, `testrun-2024-02-23-20-31/trial-02-0004/0007`, `testrun-2024-02-23-20-31/trial-04-0008/0002`, `testrun-2024-02-23-20-31/trial-04-0007/0002`, `testrun-2024-02-23-20-31/trial-03-0009/0002`, `testrun-2024-02-23-20-31/trial-03-0010/0003`

`No matching fields found for input`

Any modifications to the status field is ignored by kubernetes. This will result in no change to the system state. So it is a **false** alarm.

61 - 73. `testrun-2024-02-23-20-31/trial-00-0007/0003`, `testrun-2024-02-23-20-31/trial-01-0003/0003`, `testrun-2024-02-23-20-31/trial-08-0001/0007`, `testrun-2024-02-23-20-31/trial-08-0002/0002`, `testrun-2024-02-23-20-31/trial-02-0003/0002`, `testrun-2024-02-23-20-31/trial-02-0002/0004`, `testrun-2024-02-23-20-31/trial-04-0010/0004`, `testrun-2024-02-23-20-31/trial-08-0004/0008`, `testrun-2024-02-23-20-31/trial-08-0005/0002`, `testrun-2024-02-23-20-31/trial-04-0024/0002`, `testrun-2024-02-23-20-31/trial-04-0025/0003`

Same as 48-60. **False** alarm.

74 - 95. `testrun-2024-02-23-20-31/trial-08-0016/0001`, `testrun-2024-02-23-20-31/trial-07-0018/0001`, `testrun-2024-02-23-20-31/trial-01-0000/0002`, `testrun-2024-02-23-20-31/trial-03-0022/0002`, `testrun-2024-02-23-20-31/trial-03-0021/0002`, `testrun-2024-02-23-20-31/trial-03-0019/0002`, `testrun-2024-02-23-20-31/trial-03-0020/0002`, `testrun-2024-02-23-20-31/trial-03-0018/0002`, `testrun-2024-02-23-20-31/trial-08-0019/0002`, `testrun-2024-02-23-20-31/trial-08-0020/0002`, `testrun-2024-02-23-20-31/trial-08-0009/0005`, `testrun-2024-02-23-20-31/trial-08-0010/0003`, `testrun-2024-02-23-20-31/trial-02-0017/0002`, `testrun-2024-02-23-20-31/trial-02-0018/0003`, `testrun-2024-02-23-20-31/trial-01-0014/0003`, `testrun-2024-02-23-20-31/trial-01-0015/0003`, `testrun-2024-02-23-20-31/trial-05-0011/0003`, `testrun-2024-02-23-20-31/trial-05-0012/0003`, `testrun-2024-02-23-20-31/trial-00-0015/0005`, `testrun-2024-02-23-20-31/trial-00-0016/0001`, `testrun-2024-02-23-20-31/trial-01-0013/0003`

Same as 48-60. **False** alarm.

96. `testrun-2024-02-23-20-31/trial-00-0000/0008`

Number of replicas are set to 1000, which is not allowed. This leads to an error since the operator does not check for it.

**Misoperation**

