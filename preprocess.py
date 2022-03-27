from kubernetes.client import models, AppsV1Api, ApiextensionsV1Api
import subprocess
import logging
from typing import List, Optional
import os
import json
import schema


def preload_images(context: dict):
    '''Preload some frequently used images into Kind cluster to avoid ImagePullBackOff

    Uses global context
    '''
    if len(context['preload_images']) == 0:
        logging.error(
            'No image to preload, we at least should have operator image')

    for image in context['preload_images']:
        p = subprocess.run(['kind', 'load', 'docker-image', image])
        if p.returncode != 0:
            logging.info('Image not present local, pull and retry')
            os.system('docker pull %s' % image)
            p = subprocess.run(['kind', 'load', 'docker-image', image])


def process_crd(context: dict, crd_name: Optional[str] = None):
    ''' Get crd from k8s and set context['crd']

    When there are more than one crd in the cluster, user should set crd_name
    '''
    apiextensionsV1Api = ApiextensionsV1Api()
    crds: List[models.V1CustomResourceDefinition] = apiextensionsV1Api.list_custom_resource_definition().items
    crd: Optional[models.V1CustomResourceDefinition] = None
    if len(crds) == 0:
        logging.error(
            'No crd is found')
        quit()
    elif len(crds) == 1:
        crd = crds[0]
    elif crd_name:
        for c in crds:
            if c.metadata.name == crd_name:
                crd = c
                break
        if not crd:
            logging.error(
                'Cannot find crd %s' % crd_name)
            quit()
    else:
        logging.error(
            'There are multiple crds, please specify parameter [crd_name]')
        quit()
    if crd:
        # there is openAPIV3Schema schema issue when using python k8s client, need to fetch data from cli
        crd_result = subprocess.run(
            ['kubectl', 'get', 'crd', crd.metadata.name, "-o", "json"], capture_output=True, text=True)
        crd_obj = json.loads(crd_result.stdout)
        spec: models.V1CustomResourceDefinitionSpec = crd.spec
        crd_data = {
            'group': spec.group,
            'plural': spec.names.plural,
            'version': spec.versions[0].name,  # TODO: Handle multiple versions
            'spec_schema':
                schema.extract_schema(
                    ['root'], crd_obj['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec'])
        }
        context['crd'] = crd_data


def add_acto_label(context: dict):
    '''Add acto label to deployment, stateful_state and corresponding pods.
    '''
    appv1Api = AppsV1Api()
    operator_deployments = appv1Api.list_namespaced_deployment(
        context['namespace'],
        watch=False).items
    operator_stateful_states = appv1Api.list_namespaced_stateful_set(
        context['namespace'],
        watch=False).items
    for deployment in operator_deployments:
        patches = [
            {"metadata": {"labels": {"acto/tag": "operator-deployment"}}},
            {"spec": {"template": {"metadata": {"labels": {"acto/tag": "operator-pod"}}}}}
        ]
        for patch in patches:
            appv1Api.patch_namespaced_deployment(
                deployment.metadata.name, deployment.metadata.namespace, patch)
    for stateful_state in operator_stateful_states:
        patches = [
            {"metadata": {"labels": {"acto/tag": "operator-stateful-set"}}},
            {"spec": {"template": {"metadata": {"labels": {"acto/tag": "operator-pod"}}}}}
        ]
        for patch in patches:
            appv1Api.patch_namespaced_stateful_set(
                stateful_state.metadata.name, deployment.metadata.namespace, patch)
