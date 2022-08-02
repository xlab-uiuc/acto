import subprocess
import logging
import os
import yaml

import k8s_cluster.base as base
from constant import CONST


class K3D(base.KubernetesCluster):
    def configure_cluster(self, num_nodes: int, version: str):
        '''Create config file for k3d
        '''
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

        config_path = os.path.join(CONST.CLUSTER_CONFIG_FOLDER, 'K3D.yaml')

        if not os.path.exists(config_path):
            with open(config_path, 'w') as config_file:
                yaml.dump(config_dict, config_file)

    def get_context_name(self, cluster_name: str) -> str:
        '''Returns the kubecontext based onthe cluster name
        K3d always adds `k3d` before the cluster name
        '''
        return f'k3d-{cluster_name}'

    def create_cluster(self, name: str, config: str, version: str):
        '''Use subprocess to create k3d cluster
        Args:
            name: of the k3d cluster
            config: path of the config file for cluster
            version: k8s version
        '''
        cmd = ['k3d', 'cluster', 'create']
        
        if name:
            cmd.extend([name])
        else:
            cmd.extend([CONST.CLUSTER_NAME])
        
        if config:
            cmd.extend(['--config', config])

        return subprocess.run(cmd)
    
    def load_images(self, images_archive_path: str, name: str):
        cmd = ['k3d', 'image', 'import']

        if images_archive_path == None:
            logging.warning('No image to preload, we at least should have operator image')
        
        cmd.extend([images_archive_path])

        if name != None:
            cmd.extend(['-c', name])
        else:
            logging.error('Missing cluster name for k3d load')        
        
        if subprocess.run(cmd).returncode != 0:
            logging.error('Failed to preload images archive')

    def delete_cluster(self, name: str):
        cmd = ['k3d', 'cluster', 'delete']

        if name:
            cmd.extend([name])
        else:
            logging.error('Missing cluster name for k3d delete')
        
        while subprocess.run(cmd).returncode != 0:
            continue


if __name__ == "__main__":
    k3d = K3D()
    k3d.configure_cluster(3, '1.22.9')
    k3d.create_cluster("test-cluster", os.path.join(CONST.CLUSTER_CONFIG_FOLDER, 'K3D.yaml'), "1.22.9")
