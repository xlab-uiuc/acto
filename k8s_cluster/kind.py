import os
import yaml
import subprocess
import logging
import time
import kubernetes

from constant import CONST
import k8s_cluster.base as base


class Kind(base.KubernetesCluster):
    def __init__(self):
        self.config_path = os.path.join(
            CONST.CLUSTER_CONFIG_FOLDER, 'KIND.yaml')

    def configure_cluster(self, num_nodes: int, version: str):
        '''Create config file for kind'''
        config_dict = {}
        config_dict = {}
        config_dict['kind'] = 'Cluster'
        config_dict['apiVersion'] = 'kind.x-k8s.io/v1alpha4'
        config_dict['nodes'] = []
        extra_mounts = []
        extra_mounts.append({
            'hostPath': 'profile/data',
            'containerPath': '/tmp/profile'
        })
        for _ in range(num_nodes - 1):
            config_dict['nodes'].append({'role': 'worker', 'extraMounts': [{
                'hostPath': 'profile/data',
                'containerPath': '/tmp/profile'
            }]})
        for _ in range(1):
            config_dict['nodes'].append({'role': 'control-plane', 'extraMounts': [{
                'hostPath': 'profile/data',
                'containerPath': '/tmp/profile'
            }]})

        try:
            os.mkdir(CONST.CLUSTER_CONFIG_FOLDER)
        except FileExistsError:
            pass

        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as config_file:
                yaml.dump(config_dict, config_file)

    def get_context_name(self, cluster_name: str) -> str:
        '''Returns the kubecontext based onthe cluster name
        KIND always adds `kind` before the cluster name
        '''
        return f'kind-{cluster_name}'

    def create_cluster(self, name: str, version: str):
        '''Use subprocess to create kind cluster
        Args:
            name: name of the kind cluster
            config: path of the config file for cluster
            version: k8s version
        '''
        cmd = ['kind', 'create', 'cluster']

        if name:
            cmd.extend(['--name', name])
        else:
            cmd.extend(['--name', CONST.CLUSTER_NAME])

        cmd.extend(['--config', self.config_path])

        if version:
            cmd.extend(['--image', f"kindest/node:v{version}"])

        p = subprocess.run(cmd)
        while p.returncode != 0:
            logging.error('Failed to create kind cluster, retrying')
            self.delete_cluster(name)
            time.sleep(5)
            p = subprocess.run(cmd)

        try:
            kubernetes.config.load_kube_config(
                context=self.get_context_name(name))
        except Exception as e:
            logging.debug("Incorrect kube config file:")
            with open(f"{os.getenv('HOME')}/.kube/config") as f:
                logging.debug(f.read())
            raise e

    def load_images(self, images_archive_path: str, name: str):
        logging.info('Loading preload images')
        cmd = ['kind', 'load', 'image-archive']
        if images_archive_path == None:
            logging.warning(
                'No image to preload, we at least should have operator image')

        if name != None:
            cmd.extend(['--name', name])
        else:
            logging.error('Missing cluster name for kind load')

        p = subprocess.run(cmd + [images_archive_path])
        if p.returncode != 0:
            logging.error('Failed to preload images archive')

    def delete_cluster(self, name: str):
        cmd = ['kind', 'delete', 'cluster']

        if name:
            cmd.extend(['--name', name])
        else:
            logging.error('Missing cluster name for kind delete')

        while subprocess.run(cmd).returncode != 0:
            continue

    def get_node_list(self, name: str):
        '''Get agent containers list of a K3S cluster
        Args:
            1. Name of the cluster
        '''
        worker_name_template = '%s-worker'
        control_plane_name_template = '%s-control-plane'

        if name == None:
            name = CONST.CLUSTER_NAME

        res = super().get_node_list(worker_name_template % name) + \
            super().get_node_list(control_plane_name_template % name)

        if len(res) == 0:
            # no worker node can be found
            logging.CRITICAL(f"No node for cluster {name} can be found")
            raise RuntimeError

        return res
