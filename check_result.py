import kubernetes
from common import p_print, p_debug, p_error
from Test import workdir_name

def check_result(metadata: dict, generation: int):
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

    with open('%s/operator-%d.log' % (workdir_name, generation), 'w') as fout:
        fout.write(log)

    return