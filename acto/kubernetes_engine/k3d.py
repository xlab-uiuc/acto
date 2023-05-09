import subprocess
import os
import yaml
import time
import kubernetes
from . import base

from constant import CONST
from utils import get_thread_logger


class K3D(base.KubernetesCluster):

    def __init__(self):
        self.config_path = os.path.join(CONST.CLUSTER_CONFIG_FOLDER, 'K3D.yaml')

    def configure_cluster(self, num_nodes: int, version: str):
        '''Create config file for k3d'''
        config_dict = {}
        config_dict['apiVersion'] = 'k3d.io/v1alpha4'
        config_dict['kind'] = "Simple"
        config_dict['image'] = f'rancher/k3s:v{version}-k3s1'

        if num_nodes > 1:
            config_dict['servers'] = 1
            config_dict['agents'] = num_nodes - 1
        elif num_nodes == 1:
            config_dict['servers'] = 1

        try:
            os.mkdir(CONST.CLUSTER_CONFIG_FOLDER)
        except FileExistsError:
            pass

        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as config_file:
                yaml.dump(config_dict, config_file)

    def get_context_name(self, cluster_name: str) -> str:
        '''Returns the kubecontext based onthe cluster name
        K3d always adds `k3d` before the cluster name
        '''
        return f'k3d-{cluster_name}'

    def create_cluster(self, name: str, version: str):
        '''Use subprocess to create k3d cluster
        Args:
            name: of the k3d cluster
            config: path of the config file for cluster
            version: k8s version
        '''
        logger = get_thread_logger(with_prefix=False)

        cmd = ['k3d', 'cluster', 'create']

        if name:
            cmd.extend([name])
        else:
            cmd.extend([CONST.CLUSTER_NAME])

        cmd.extend(['--config', self.config_path])

        p = subprocess.run(cmd)
        while p.returncode != 0:
            logger.error('Failed to create k3d cluster, retrying')
            self.delete_cluster(name)
            time.sleep(5)
            p = subprocess.run(cmd)

        try:
            kubernetes.config.load_kube_config(context=self.get_context_name(name))
        except Exception as e:
            logger.debug("Incorrect kube config file:")
            with open(f"{os.getenv('HOME')}/.kube/config") as f:
                logger.debug(f.read())
            raise e

    def load_images(self, images_archive_path: str, name: str):
        logger = get_thread_logger(with_prefix=False)

        logger.info('Loading preload images')
        cmd = ['k3d', 'image', 'import']

        if images_archive_path == None:
            logger.warning('No image to preload, we at least should have operator image')

        cmd.extend([images_archive_path])

        if name != None:
            cmd.extend(['-c', name])
        else:
            cmd.extend(['-c', CONST.CLUSTER_NAME])

        if subprocess.run(cmd).returncode != 0:
            logger.error('Failed to preload images archive')

    def delete_cluster(self, name: str):
        logger = get_thread_logger(with_prefix=False)

        cmd = ['k3d', 'cluster', 'delete']

        if name:
            cmd.extend([name])
        else:
            logger.error('Missing cluster name for k3d delete')

        while subprocess.run(cmd).returncode != 0:
            continue

    def get_node_list(self, name: str):
        '''Get container list of a K3S cluster
        Args:
            1. Name of the cluster
        '''
        logger = get_thread_logger(with_prefix=False)

        worker_name_template = 'k3d-%s-agent-'
        control_plane_name_template = 'k3d-%s-server-'

        if name == None:
            name = CONST.CLUSTER_NAME

        res = super().get_node_list(worker_name_template % name) + \
            super().get_node_list(control_plane_name_template % name)

        if len(res) == 0:
            # no worker node can be found
            logger.CRITICAL(f"No node for cluster {name} can be found")
            raise RuntimeError

        return res


if __name__ == "__main__":
    k3d = K3D()
    k3d.configure_cluster(3, '1.22.9')
    k3d.create_cluster("test-cluster", os.path.join(CONST.CLUSTER_CONFIG_FOLDER, 'K3D.yaml'),
                       "1.22.9")
