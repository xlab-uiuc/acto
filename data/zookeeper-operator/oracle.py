import json
from typing import List
from client.oracle_handle import OracleHandle
from common import ErrorResult, Oracle, PassResult, RunResult, canonicalize
from thread_logger import get_thread_logger


def zookeeper_checker(handle: OracleHandle) -> RunResult:
    '''Checks the health of the Zookeeper cluster'''

    cr = handle.get_cr()
    if 'config' in cr['spec']:
        config = cr['spec']['config']
        if 'additionalConfig' in config and config['additionalConfig'] != None:
            for key, value in config['additionalConfig'].items():
                config[key] = value
            del config['additionalConfig']
    else:
        config = None

    sts_list = handle.get_stateful_sets()

    if len(sts_list) != 1:
        return ErrorResult(oracle=Oracle.CUSTOM,
                           msg='Zookeeper cluster has more than one stateful set')

    pod_list = handle.get_pods_in_stateful_set(sts_list[0])

    leaders = 0
    for pod in pod_list:
        if pod.status.pod_ip == None:
            return ErrorResult(oracle=Oracle.CUSTOM,
                               msg='Zookeeper pod does not have an IP assigned')
        p = handle.kubectl_client.exec(
            pod.metadata.name,
            pod.metadata.namespace, ['curl', 'http://' + pod.status.pod_ip + ':8080/commands/ruok'],
            capture_output=True,
            text=True)
        result = json.loads(p.stdout)
        if result['error'] != None:
            return ErrorResult(oracle=Oracle.CUSTOM,
                               msg='Zookeeper cluster curl has error ' + result['error'])

        p = handle.kubectl_client.exec(
            pod.metadata.name,
            pod.metadata.namespace, ['curl', 'http://' + pod.status.pod_ip + ':8080/commands/stat'],
            capture_output=True,
            text=True)
        result = json.loads(p.stdout)
        if result['error'] != None:
            return ErrorResult(oracle=Oracle.CUSTOM,
                               msg='Zookeeper cluster curl has error ' + result['error'])
        elif result['server_stats']['server_state'] == 'leader':
            leaders += 1

        if config != None:
            p = handle.kubectl_client.exec(
                pod.metadata.name,
                pod.metadata.namespace,
                ['curl', 'http://' + pod.status.pod_ip + ':8080/commands/conf'],
                capture_output=True,
                text=True)
            result = json.loads(p.stdout)
            if result['error'] != None:
                return ErrorResult(oracle=Oracle.CUSTOM,
                                   msg='Zookeeper cluster curl has error ' + result['error'])

            for key, value in config.items():
                canonicalize_key = canonicalize(key)
                if canonicalize_key not in result:
                    return ErrorResult(oracle=Oracle.CUSTOM,
                                       msg='Zookeeper config does not contain key ' + key)
                elif result[canonicalize_key] != value:
                    return ErrorResult(oracle=Oracle.CUSTOM,
                                       msg='Zookeeper cluster has incorrect config')

    if leaders > 1:
        return ErrorResult(oracle=Oracle.CUSTOM, msg='Zookeeper cluster has more than one leader')

    p = handle.kubectl_client.exec('zkapp',
                                   handle.namespace, ['request'],
                                   capture_output=True,
                                   text=True)
    if p.returncode != 0:
        return ErrorResult(oracle=Oracle.CUSTOM, msg='Zookeeper app request failed')
    elif p.stdout != 'test':
        return ErrorResult(oracle=Oracle.CUSTOM,
                           msg='Zookeeper app request result wrong %s' % p.stdout)

    return PassResult()


def deploy_zk_app(handle: OracleHandle):
    handle.kubectl_client.kubectl([
        'run', 'zkapp', '--image=tylergu1998/zkapp:v1', '-l', 'acto/tag=custom-oracle', '-n',
        handle.namespace
    ])


CUSTOM_CHECKER: List[callable] = [zookeeper_checker]
ON_INIT: List[callable] = [deploy_zk_app]
