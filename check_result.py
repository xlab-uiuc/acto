from cgitb import text
import kubernetes
import subprocess

from common import p_print, p_debug, p_error, RunResult
from Test import workdir_name

def run_and_check(cmd: list, metadata: dict, generation: int) -> RunResult:
    cli_result = subprocess.run(cmd, capture_output=True, text=True)
    
    if cli_result.stdout.find('error') != -1 or cli_result.stderr.find('error') != -1:
        p_error('Invalid input, reject mutation')
        p_error('STDOUT: ' + cli_result.stdout)
        p_error('STDERR: ' + cli_result.stderr)
        return RunResult.invalidInput
    
    if cli_result.stdout.find('unchanged') != -1 or cli_result.stderr.find('unchanged') != -1:
        p_error('CR unchanged, continue')
        return RunResult.unchanged
    
    kubernetes.config.load_kube_config()
    corev1 = kubernetes.client.CoreV1Api()
    operator_pod_list = corev1.list_namespaced_pod(
        namespace=metadata['namespace'],
        watch=False,
        label_selector="testing/tag=operator-pod"
    ).items
    if len(operator_pod_list) >= 1:
        p_debug('Got operator pod: pod name:'+operator_pod_list[0].metadata.name)
    else:
        p_error('Failed to find operator pod')

    log = corev1.read_namespaced_pod_log(
        name=operator_pod_list[0].metadata.name,
        namespace=metadata['namespace']
    )

    if log.find('error') != -1:
        p_print('Found error in operator log')
        return RunResult.error

    with open('%s/operator-%d.log' % (workdir_name, generation), 'w') as fout:
        fout.write(log)

    return RunResult.passing