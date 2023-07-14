from dataclasses import dataclass, field, asdict
from typing import Dict, List

from acto.checker.checker import Checker, OracleControlFlow, OracleResult
from acto.lib.dict import visit_dict
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger


@dataclass
class HealthResult(OracleResult):
    unhealthy_resources: Dict[str, List[str]] = field(default_factory=dict)

    def __init__(self, unhealthy_resources: Dict[str, List[str]] = None):
        if unhealthy_resources is None:
            unhealthy_resources = {}
        logger = get_thread_logger(with_prefix=True)
        error_msgs = []
        filtered_unhealthy_resources = {}
        for kind, resources in unhealthy_resources.items():
            if len(resources) != 0:
                error_msgs.append(f"{kind}: {', '.join(resources)}")
                logger.error(f"Found {kind}: {', '.join(resources)} with unhealthy status")
                filtered_unhealthy_resources[kind] = resources
        self.unhealthy_resources = filtered_unhealthy_resources
        if len(error_msgs) == 0:
            error_msgs = [OracleControlFlow.ok]
        error_msgs = sorted(error_msgs)
        super().__init__('\n'.join(error_msgs))


class HealthChecker(Checker):
    name = 'health'

    def _check(self, snapshot: Snapshot, __: Snapshot) -> OracleResult:
        """System health oracle"""
        system_state = snapshot.system_state
        unhealthy_resources = {
            'statefulset': [],
            'deployment': [],
            'pod': [],
            'cr': []
        }

        # check Health of Statefulsets
        for sfs in system_state['stateful_set'].values():
            if sfs['status']['ready_replicas'] is None and sfs['spec']['replicas'] == 0:
                # replicas could be 0
                continue
            if sfs['spec']['replicas'] != sfs['status']['ready_replicas']:
                unhealthy_resources['statefulset'].append(
                    '%s replicas [%s] ready_replicas [%s]' %
                    (sfs['metadata']['name'], sfs['status']['replicas'],
                     sfs['status']['ready_replicas']))

        # check Health of Deployments
        for dp in system_state['deployment'].values():
            if dp['spec']['replicas'] == 0:
                continue

            if dp['spec']['replicas'] != dp['status']['ready_replicas']:
                unhealthy_resources['deployment'].append(
                    '%s replicas [%s] ready_replicas [%s]' %
                    (dp['metadata']['name'], dp['status']['replicas'],
                     dp['status']['ready_replicas']))

            for condition in dp['status']['conditions']:
                if condition['type'] == 'Available' and condition['status'] != 'True':
                    unhealthy_resources['deployment'].append(
                        '%s condition [%s] status [%s] message [%s]' %
                        (dp['metadata']['name'], condition['type'], condition['status'],
                         condition['message']))
                elif condition['type'] == 'Progressing' and condition['status'] != 'True':
                    unhealthy_resources['deployment'].append(
                        '%s condition [%s] status [%s] message [%s]' %
                        (dp['metadata']['name'], condition['type'], condition['status'],
                         condition['message']))

        # check Health of Pods
        for pod in system_state['pod'].values():
            if pod['status']['phase'] in ['Running', 'Completed', 'Succeeded']:
                continue
            unhealthy_resources['pod'].append(pod['metadata']['name'])

        for deployment in system_state['deployment_pods'].values():
            for pod in deployment:
                if pod['status']['phase'] in ['Completed', 'Succeeded']:
                    continue

                if 'container_statuses' in pod['status'] and pod['status']['container_statuses']:
                    for container in pod['status']['container_statuses']:
                        if container['restart_count'] > 0:
                            unhealthy_resources['pod'].append(
                                '%s container [%s] restart_count [%s]' %
                                (pod['metadata']['name'], container['name'],
                                 container['restart_count']))

        # check Health of CRs
        _, conditions = visit_dict(system_state, ['custom_resource_status', 'conditions'])
        if conditions is not None:
            for condition in system_state['custom_resource_status']['conditions']:
                if condition['type'] == 'Ready' and condition['status'] != 'True' and 'is forbidden' in condition['message'].lower():
                    unhealthy_resources['cr'].append('%s condition [%s] status [%s] message [%s]' %
                                                     ('CR status unhealthy', condition['type'],
                                                      condition['status'], condition['message']))

        return HealthResult(unhealthy_resources)
