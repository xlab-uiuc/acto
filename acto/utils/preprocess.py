import json
import subprocess
from typing import List, Optional

import kubernetes
import yaml

from acto.kubectl_client import KubectlClient

from .thread_logger import get_thread_logger


def update_preload_images(context: dict, worker_list):
    """Get used images from pod
    """
    logger = get_thread_logger(with_prefix=False)

    namespace = context.get('namespace', '')
    if not namespace:
        return

    k8s_images = [
        'docker.io/kindest/kindnetd',
        'docker.io/rancher/local-path-provisioner',
        'docker.io/kindest/local-path-provisioner',
        'docker.io/kindest/local-path-helper',
        'k8s.gcr.io/build-image/debian-base',
        'k8s.gcr.io/coredns/coredns',
        'k8s.gcr.io/etcd',
        'k8s.gcr.io/kube-apiserver',
        'k8s.gcr.io/kube-controller-manager',
        'k8s.gcr.io/kube-proxy',
        'k8s.gcr.io/kube-scheduler',
        'k8s.gcr.io/pause',
        'docker.io/rancher/klipper-helm',
        'docker.io/rancher/klipper-lb',
        'docker.io/rancher/mirrored-coredns-coredns',
        'docker.io/rancher/mirrored-library-busybox',
        'docker.io/rancher/mirrored-library-traefik',
        'docker.io/rancher/mirrored-metrics-server',
        'docker.io/rancher/mirrored-paus',
    ]

    for worker in worker_list:
        p = subprocess.run(
            ['docker', 'exec', worker, 'crictl', 'images', "--digests", "--no-trunc"],
            capture_output=True,
            text=True)
        output = p.stdout.strip()
        for line in output.split('\n')[1:]:
            items = line.split()
            if items[0] in k8s_images:
                continue
            if "none" not in items[1]:
                image = '%s:%s' % (items[0], items[1])
            else:
                logger.warning(
                    "image %s has no tag, acto will not preload this image for this run" %
                    (items[0]))
                continue

            context['preload_images'].add(image)


def process_crd(context: dict,
                apiclient: kubernetes.client.ApiClient,
                kubectl_client: KubectlClient,
                crd_name: Optional[str] = None,
                helper_crd: Optional[str] = None):
    ''' Get crd from k8s and set context['crd']

    When there are more than one crd in the cluster, user should set crd_name
    '''
    logger = get_thread_logger(with_prefix=False)

    if helper_crd == None:
        apiextensionsV1Api = kubernetes.client.ApiextensionsV1Api(apiclient)
        crds: List[
            kubernetes.client.models.
            V1CustomResourceDefinition] = apiextensionsV1Api.list_custom_resource_definition().items
        crd: Optional[kubernetes.client.models.V1CustomResourceDefinition] = None
        if len(crds) == 0:
            logger.error('No crd is found')
            quit()
        elif len(crds) == 1:
            crd = crds[0]
        elif crd_name:
            for c in crds:
                if c.metadata.name == crd_name:
                    crd = c
                    break
            if not crd:
                logger.error('Cannot find crd %s' % crd_name)
                quit()
        else:
            logger.error('There are multiple crds, please specify parameter [crd_name]')
            quit()
        if crd:
            # there is openAPIV3Schema schema issue when using python k8s client, need to fetch data from cli
            crd_result = kubectl_client.kubectl(['get', 'crd', crd.metadata.name, "-o", "json"],
                                                True, True)
            crd_obj = json.loads(crd_result.stdout)
            spec: kubernetes.client.models.V1CustomResourceDefinitionSpec = crd.spec
            crd_data = {
                'group': spec.group,
                'plural': spec.names.plural,
                # TODO: Handle multiple versions
                'version': spec.versions[0].name,
                'body': crd_obj
            }
            context['crd'] = crd_data
    else:
        with open(helper_crd, 'r') as helper_crd_f:
            helper_crd_doc = yaml.load(helper_crd_f, Loader=yaml.FullLoader)
        crd_data = {
            'group': helper_crd_doc['spec']['group'],
            'plural': helper_crd_doc['spec']['names']['plural'],
            'version': helper_crd_doc['spec']['versions'][-1]
                       ['name'],  # TODO: Handle multiple versions
            'body': helper_crd_doc
        }
        context['crd'] = crd_data


def add_acto_label(apiclient: kubernetes.client.ApiClient, context: dict):
    '''Add acto label to deployment, stateful_state and corresponding pods.
    '''
    appv1Api = kubernetes.client.AppsV1Api(apiclient)
    operator_deployments = appv1Api.list_namespaced_deployment(context['namespace'],
                                                               watch=False).items
    operator_stateful_states = appv1Api.list_namespaced_stateful_set(context['namespace'],
                                                                     watch=False).items
    for deployment in operator_deployments:
        patches = [{
            "metadata": {
                "labels": {
                    "acto/tag": "operator-deployment"
                }
            }
        }, {
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {
                            "acto/tag": "operator-pod"
                        }
                    }
                }
            }
        }]
        for patch in patches:
            appv1Api.patch_namespaced_deployment(deployment.metadata.name,
                                                 deployment.metadata.namespace, patch)
    for stateful_state in operator_stateful_states:
        patches = [{
            "metadata": {
                "labels": {
                    "acto/tag": "operator-stateful-set"
                }
            }
        }, {
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {
                            "acto/tag": "operator-pod"
                        }
                    }
                }
            }
        }]
        for patch in patches:
            appv1Api.patch_namespaced_stateful_set(stateful_state.metadata.name,
                                                   deployment.metadata.namespace, patch)
