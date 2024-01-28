import logging
import os
import subprocess
import time
from typing import List

import kubernetes

from acto.common import kubernetes_client, print_event
from acto.constant import CONST

from . import base


class Minikube(base.KubernetesEngine):

    def __init__(
            self, acto_namespace: int, posthooks: List[base.KubernetesEnginePostHookType] = None, num_nodes = 1, version = ""):
        self.config_path = os.path.join(CONST.CLUSTER_CONFIG_FOLDER, f'MINIKUBE-{acto_namespace}.yaml')
        self.num_nodes = num_nodes
        self._k8s_version = version
        if posthooks is not None:
            self.posthooks = posthooks

    def configure_cluster(self, num_nodes: int, version: str, name = ""):
        '''Create config file for kind'''
        self.num_nodes = num_nodes
        self._k8s_version = version
        

    def get_context_name(self, cluster_name: str) -> str:
        '''Returns the kubecontext based onthe cluster name
        KIND always adds `kind` before the cluster name
        '''
        pass
    
    def create_cluster(self, name: str, kubeconfig: str):
        '''Use subprocess to create kind cluster
        Args:
            name: name of the kind cluster
            config: path of the config file for cluster
            version: k8s version
        '''
        print_event('Creating a Minikube cluster...')
        cmd = ['minikube', 'start']

        if name:
            cmd.extend(['--profile', name])
        else:
            cmd.extend(['--profile', CONST.CLUSTER_NAME])
            
        if kubeconfig:
            logging.info(f'Kubeconfig: {kubeconfig}')
            os.environ["KUBECONFIG"] = kubeconfig
        else:
            raise Exception('Missing kubeconfig for kind create')
        
        cmd.extend(['--nodes', str(self.num_nodes)])
        
        if self._k8s_version != "":
            cmd.extend(['--kubernetes-version', str(self._k8s_version)])              
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        i = 0
        while p.returncode != 0:
            if i == 3:
                # tried 3 times, still failed
                logging.error('Failed to create minikube cluster, aborting')
                raise Exception('Failed to create minikube cluster')

            logging.error('Failed to create minikube cluster, retrying')
            i += 1
            self.delete_cluster(name, kubeconfig)
            time.sleep(5)
            p = subprocess.run(cmd)

        # csi driver
        cmd = ['minikube', 'addons', 'disable', 'storage-provisioner']
        cmd.extend(['--profile', name])
        
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        i = 0
        print(cmd)
        while p.returncode != 0:
            if i == 3:
                # tried 3 times, still failed
                logging.error('Failed to create minikube cluster, aborting')
                raise Exception('Failed to create minikube cluster')

            logging.error('Failed to create minikube cluster, retrying')
            i += 1
            self.delete_cluster(name, kubeconfig)
            time.sleep(5)
            p = subprocess.run(cmd)
        
        cmd = ['minikube', 'addons', 'disable', 'default-storageclass']
        cmd.extend(['--profile', name])
        
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        i = 0
        print(cmd)
        while p.returncode != 0:
            if i == 3:
                # tried 3 times, still failed
                logging.error('Failed to create minikube cluster, aborting')
                raise Exception('Failed to create minikube cluster')

            logging.error('Failed to create minikube cluster, retrying')
            i += 1
            self.delete_cluster(name, kubeconfig)
            time.sleep(5)
            p = subprocess.run(cmd)
        
        cmd = ['minikube', 'addons', 'enable', 'volumesnapshots']
        cmd.extend(['--profile', name])
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        i = 0
        print(cmd)
        while p.returncode != 0:
            if i == 3:
                # tried 3 times, still failed
                logging.error('Failed to create minikube cluster, aborting')
                raise Exception('Failed to create minikube cluster')

            logging.error('Failed to create minikube cluster, retrying')
            i += 1
            self.delete_cluster(name, kubeconfig)
            time.sleep(5)
            p = subprocess.run(cmd)
        
        cmd = ['minikube', 'addons', 'enable', 'csi-hostpath-driver']
        cmd.extend(['--profile', name])
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        i = 0
        print(cmd)
        while p.returncode != 0:
            if i == 3:
                # tried 3 times, still failed
                logging.error('Failed to create minikube cluster, aborting')
                raise Exception('Failed to create minikube cluster')

            logging.error('Failed to create minikube cluster, retrying')
            i += 1
            self.delete_cluster(name, kubeconfig)
            time.sleep(5)
            p = subprocess.run(cmd) 
        
        cmd = ['kubectl', 'patch', 'storageclass', 'csi-hostpath-sc', '-p', '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}']
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        i = 0
        print(cmd)
        while p.returncode != 0:
            if i == 3:
                # tried 3 times, still failed
                logging.error('Failed to create minikube cluster, aborting')
                raise Exception('Failed to create minikube cluster')

            logging.error('Failed to create minikube cluster, retrying')
            i += 1
            self.delete_cluster(name, kubeconfig)
            time.sleep(5)
            p = subprocess.run(cmd)
            
        # minikube mount
        cmd = ['minikube', 'mount', 'profile/data:/tmp/profile']
        cmd.extend(['--profile', name])
        print(cmd)
        p2 = subprocess.Popen(cmd)
        
        try:
            kubernetes.config.load_kube_config(config_file=kubeconfig,
                                               context=name)
            apiclient = kubernetes_client(kubeconfig, name)
        except Exception as e:
            logging.debug("Incorrect kube config file:")
            with open(kubeconfig) as f:
                logging.debug(f.read())
            raise e
        os.environ.pop('KUBECONFIG', None)

    def load_images(self, images_archive_path: str, name: str):
        logging.info('Loading preload images')
        cmd = ['minikube', 'image', 'load']
        if images_archive_path == None:
            logging.warning('No image to preload, we at least should have operator image')

        if name != None:
            cmd.extend(['--profile', name])
        else:
            logging.error('Missing cluster name for kind load')

        p = subprocess.run(cmd + [images_archive_path])
        if p.returncode != 0:
            logging.error('Failed to preload images archive')

    def delete_cluster(self, name: str, kubeconfig: str):
        cmd = ['minikube', 'delete']

        if name:
            cmd.extend(['--profile', name])
        else:
            logging.error('Missing cluster name for kind delete')

        if kubeconfig:
            logging.info(f'Kubeconfig: {kubeconfig}')
            os.environ["KUBECONFIG"] = kubeconfig
        else:
            raise Exception('Missing kubeconfig for kind create')

        while subprocess.run(cmd).returncode != 0:
            continue
        
        os.environ.pop('KUBECONFIG', None)
        
    def get_node_list(self, name: str):
        '''Get agent containers list of a K3S cluster
        Args:
            1. Name of the cluster
        '''
        cmd = ['minikube', 'node', 'list']
        if name == None:
            name = CONST.CLUSTER_NAME
        else:
            cmd.extend(['--profile', name])
        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.stdout == None or p.stdout == '' or "not found" in p.stdout:
            # no nodes can be found, returning an empty array
            logging.critical(f"No node for cluster {name} can be found")
            raise RuntimeError
        return p.stdout.strip().split('\n')
