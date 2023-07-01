from acto.checker.checker import Checker
from acto.common import OracleResult, PassResult, Oracle, UnhealthyResult
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger


class HealthChecker(Checker):
    name = 'health'

    def check(self, _: int, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        """System health oracle"""
        logger = get_thread_logger(with_prefix=True)

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
        if system_state['custom_resource_status'] is not None and 'conditions' in system_state[
            'custom_resource_status']:
            for condition in system_state['custom_resource_status']['conditions']:
                if condition['type'] == 'Ready' and condition[
                    'status'] != 'True' and 'is forbidden' in condition['message'].lower():
                    unhealthy_resources['cr'].append('%s condition [%s] status [%s] message [%s]' %
                                                     ('CR status unhealthy', condition['type'],
                                                      condition['status'], condition['message']))

        error_msg = ''
        for kind, resources in unhealthy_resources.items():
            if len(resources) != 0:
                error_msg += f"{kind}: {', '.join(resources)}\n"
                logger.error(f"Found {kind}: {', '.join(resources)} with unhealthy status")

        if error_msg != '':
            return UnhealthyResult(Oracle.SYSTEM_HEALTH, error_msg)

        return PassResult()
