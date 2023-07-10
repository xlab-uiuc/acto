from acto.checker.checker import Checker, OracleResult
from acto.lib.dict import visit_dict
from acto.snapshot import Snapshot


def check_pod_status(pod):
    container_statuses = pod['status']['container_statuses']
    pod_name = pod['metadata']['name']
    if not container_statuses:
        return
    for container_status in container_statuses:
        if 'state' not in container_status:
            continue
        if visit_dict(container_status['state'], ['terminated', 'reason']) == (True, 'Error'):
            raise OracleResult('Pod %s crashed' % pod_name)
        if visit_dict(container_status['state'], ['waiting', 'reason']) == (True, 'CrashLoopBackOff'):
            raise OracleResult('Pod %s crashed' % pod_name)


class CrashChecker(Checker):
    name = 'crash'

    def _check(self, snapshot: Snapshot, __: Snapshot) -> OracleResult:
        pods = snapshot.system_state['pod']
        deployment_pods = snapshot.system_state['deployment_pods']

        try:
            for _, pod in pods.items():
                check_pod_status(pod)

            for deployment_name, deployment in deployment_pods.items():
                for pod in deployment:
                    check_pod_status(pod)

        except OracleResult as e:
            return e

        return OracleResult()
