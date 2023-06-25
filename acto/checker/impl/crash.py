from acto.checker.checker import Checker
from acto.common import OracleResult, ErrorResult, Oracle, PassResult
from acto.snapshot import Snapshot
from acto.lib.dict import visit_dict


def check_pod_status(pod):
    container_statuses = pod['status']['container_statuses']
    pod_name = pod['metadata']['name']
    if not container_statuses:
        return
    for container_status in container_statuses:
        if 'state' not in container_status:
            continue
        if visit_dict(container_status['state'], ['terminated', 'reason']) == (True, 'Error'):
            raise ErrorResult(Oracle.CRASH, 'Pod %s crashed' % pod_name)
        if visit_dict(container_status['state'], ['waiting', 'reason']) == (True, 'CrashLoopBackOff'):
            raise ErrorResult(Oracle.CRASH, 'Pod %s crashed' % pod_name)


class CrashChecker(Checker):
    name = 'crash'

    def check(self, _: int, snapshot: Snapshot, __: Snapshot) -> OracleResult:
        if snapshot.operator_log is not None:
            for line in snapshot.operator_log:
                if 'Bug!' in line:
                    return ErrorResult(Oracle.CRASH, line)

        pods = snapshot.system_state['pod']
        deployment_pods = snapshot.system_state['deployment_pods']

        try:
            for _, pod in pods.items():
                check_pod_status(pod)

            for deployment_name, deployment in deployment_pods.items():
                for pod in deployment:
                    check_pod_status(pod)

        except ErrorResult as e:
            return e

        return PassResult()
