from kubernetes.client import models, AppsV1Api, ApiextensionsV1Api
import subprocess
import logging
from typing import List, Optional
import os
import json
import yaml


def preload_images(images: list):
    '''Preload some frequently used images into Kind cluster to avoid ImagePullBackOff

    Uses global context
    '''
    if len(images) == 0:
        logging.warning(
            'No image to preload, we at least should have operator image')

    for image in images:
        p = subprocess.run(['kind', 'load', 'docker-image', image])
        if p.returncode != 0:
            logging.info('Image not present local, pull and retry')
            os.system('docker pull %s' % image)
            p = subprocess.run(['kind', 'load', 'docker-image', image])


def update_preload_images(context: dict):
    """Get used images from pod
    """
    namespace = context.get('namespace', '')
    if not namespace:
        return

    worker_list = ['kind-worker', 'kind-worker2', 'kind-worker3']
    for worker in worker_list:
        p = subprocess.run(['docker', 'exec', worker, 'crictl', 'images'],
                           capture_output=True,
                           text=True)
        output = p.stdout.strip()
        for line in output.split('\n')[1:]:
            items = line.split()
            image = '%s:%s' % (items[0], items[1])
            context['preload_images'].add(image)


def process_crd(context: dict,
                crd_name: Optional[str] = None,
                helper_crd: Optional[str] = None):
    ''' Get crd from k8s and set context['crd']

    When there are more than one crd in the cluster, user should set crd_name
    '''
    if helper_crd == None:
        apiextensionsV1Api = ApiextensionsV1Api()
        crds: List[
            models.
            V1CustomResourceDefinition] = apiextensionsV1Api.list_custom_resource_definition(
            ).items
        crd: Optional[models.V1CustomResourceDefinition] = None
        if len(crds) == 0:
            logging.error('No crd is found')
            quit()
        elif len(crds) == 1:
            crd = crds[0]
        elif crd_name:
            for c in crds:
                if c.metadata.name == crd_name:
                    crd = c
                    break
            if not crd:
                logging.error('Cannot find crd %s' % crd_name)
                quit()
        else:
            logging.error(
                'There are multiple crds, please specify parameter [crd_name]')
            quit()
        if crd:
            # there is openAPIV3Schema schema issue when using python k8s client, need to fetch data from cli
            crd_result = subprocess.run(
                ['kubectl', 'get', 'crd', crd.metadata.name, "-o", "json"],
                capture_output=True,
                text=True)
            crd_obj = json.loads(crd_result.stdout)
            spec: models.V1CustomResourceDefinitionSpec = crd.spec
            crd_data = {
                'group': spec.group,
                'plural': spec.names.plural,
                'version':
                    spec.versions[0].name,  # TODO: Handle multiple versions
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
    logging.debug('CRD data: %s' % crd_data)


def add_acto_label(context: dict):
    '''Add acto label to deployment, stateful_state and corresponding pods.
    '''
    appv1Api = AppsV1Api()
    operator_deployments = appv1Api.list_namespaced_deployment(
        context['namespace'], watch=False).items
    operator_stateful_states = appv1Api.list_namespaced_stateful_set(
        context['namespace'], watch=False).items
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
                                                 deployment.metadata.namespace,
                                                 patch)
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
            appv1Api.patch_namespaced_stateful_set(
                stateful_state.metadata.name, deployment.metadata.namespace,
                patch)
