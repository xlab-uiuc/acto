import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List

from deepdiff import DeepDiff

from acto.checker.checker import Checker, OracleResult
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger


@dataclass
class RecoveryResult(OracleResult):
    diff: DeepDiff = field(default_factory=lambda: DeepDiff({}, {}))


class RecoveryChecker(Checker):
    name = 'recovery'

    def _check(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        """
        Check whether two system state are semantically equivalent

        Args:
            - snapshot: a reference to a system state
            - prev_snapshot: a reference to another system state

        Return value:
            - a dict of diff results, empty if no diff found
        """

        if snapshot.trial_state != 'recovery':
            return OracleResult()
        prev_snapshot = prev_snapshot.snapshot_before_applied_input
        assert prev_snapshot is not None
        return compare_system_equality(snapshot.system_state, prev_snapshot.system_state)


def compare_system_equality(curr_system_state: dict,
                            prev_system_state: dict,
                            diff_operators: list = None,
                            additional_exclude_paths: List[str] = None,
                            iterable_compare_func = None) -> OracleResult:
    if diff_operators is None:
        diff_operators = []
    if additional_exclude_paths is None:
        additional_exclude_paths = []
    curr_system_state = deepcopy(curr_system_state)
    prev_system_state = deepcopy(prev_system_state)

    if len(curr_system_state) == 0 or len(prev_system_state) == 0:
        return OracleResult()

    del curr_system_state['endpoints']
    del prev_system_state['endpoints']
    del curr_system_state['job']
    del prev_system_state['job']

    # remove pods that belong to jobs from both states to avoid observability problem
    curr_pods = curr_system_state['pod']
    prev_pods = prev_system_state['pod']
    curr_system_state['pod'] = {
        k: v
        for k, v in curr_pods.items()
        if v['metadata']['owner_references'][0]['kind'] != 'Job'
    }
    prev_system_state['pod'] = {
        k: v
        for k, v in prev_pods.items()
        if v['metadata']['owner_references'][0]['kind'] != 'Job'
    }

    for name, obj in prev_system_state['secret'].items():
        if 'data' in obj and obj['data'] is not None:
            for key, data in obj['data'].items():
                try:
                    obj['data'][key] = json.loads(data)
                except:
                    pass

    for name, obj in curr_system_state['secret'].items():
        if 'data' in obj and obj['data'] is not None:
            for key, data in obj['data'].items():
                try:
                    obj['data'][key] = json.loads(data)
                except:
                    pass

    # remove custom resource from both states
    curr_system_state.pop('custom_resource_spec', None)
    prev_system_state.pop('custom_resource_spec', None)
    curr_system_state.pop('custom_resource_status', None)
    prev_system_state.pop('custom_resource_status', None)
    curr_system_state.pop('pvc', None)
    prev_system_state.pop('pvc', None)

    # remove fields that are not deterministic
    exclude_paths = [
        r".*\['metadata'\]\['managed_fields'\]",
        r".*\['metadata'\]\['cluster_name'\]",
        r".*\['metadata'\]\['creation_timestamp'\]",
        r".*\['metadata'\]\['resource_version'\]",
        r".*\['metadata'\].*\['uid'\]",
        r".*\['metadata'\]\['generation'\]$",
        r".*\['metadata'\]\['annotations'\]",
        r".*\['metadata'\]\['annotations'\]\['.*last-applied.*'\]",
        r".*\['metadata'\]\['annotations'\]\['.*\.kubernetes\.io.*'\]",
        r".*\['metadata'\]\['labels'\]\['.*revision.*'\]",
        r".*\['metadata'\]\['labels'\]\['owner-rv'\]",
        r".*\['status'\]",
        r"\['metadata'\]\['deletion_grace_period_seconds'\]",
        r"\['metadata'\]\['deletion_timestamp'\]",
        r".*\['spec'\]\['init_containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['containers'\]\[.*\]\['volume_mounts'\]\[.*\]\['name'\]$",
        r".*\['spec'\]\['volumes'\]\[.*\]\['name'\]$",
        r".*\[.*\]\['node_name'\]$",
        r".*\[\'spec\'\]\[\'host_users\'\]$",
        r".*\[\'spec\'\]\[\'os\'\]$",
        r".*\[\'grpc\'\]$",
        r".*\[\'spec\'\]\[\'volume_name\'\]$",
        r".*\['version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['uid'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['target_ref'\]\['resource_version'\]$",
        r".*\['endpoints'\]\[.*\]\['addresses'\]\[.*\]\['ip'\]",
        r".*\['cluster_ip'\]$",
        r".*\['cluster_i_ps'\].*$",
        r".*\['deployment_pods'\].*\['metadata'\]\['name'\]$",
        r"\[\'config_map\'\]\[\'kube\-root\-ca\.crt\'\]\[\'data\'\]\[\'ca\.crt\'\]$",
        r".*\['secret'\].*$",
        r"\['secrets'\]\[.*\]\['name'\]",
        r".*\['node_port'\]",
        r".*\['metadata'\]\['generate_name'\]",
        r".*\['metadata'\]\['labels'\]\['pod\-template\-hash'\]",
        r"\['deployment_pods'\].*\['metadata'\]\['owner_references'\]\[.*\]\['name'\]",
    ] + additional_exclude_paths

    diff = DeepDiff(prev_system_state,
                    curr_system_state,
                    exclude_regex_paths=exclude_paths,
                    custom_operators=diff_operators,
                    iterable_compare_func=iterable_compare_func,
                    view='tree')

    if diff:
        message = f"failed attempt recovering to seed state - system state diff: {diff}"
        logging.debug(message)
        return RecoveryResult(message=message, diff=diff)

    return OracleResult()
