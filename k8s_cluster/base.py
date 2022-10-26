import subprocess
import time
from abc import ABC, abstractmethod

from constant import CONST
from thread_logger import get_thread_logger


class KubernetesCluster(ABC):
    @abstractmethod
    def configure_cluster(self, num_nodes: int, version: str):
        pass

    @abstractmethod
    def get_context_name(self, cluster_name: str) -> str:
        pass

    @abstractmethod
    def create_cluster(self, name: str, kubeconfig: str, version: str):
        pass

    @abstractmethod
    def load_images(self, images_archive_path: str, name: str):
        pass

    @abstractmethod
    def delete_cluster(self, name: str, kubeconfig: str, ):
        pass

    def restart_cluster(self, name: str, kubeconfig: str, version: str):
        logger = get_thread_logger(with_prefix=False)
        
        retry_count = 3

        while (retry_count > 0):
            try:
                self.delete_cluster(name, kubeconfig)
                time.sleep(1)
                self.create_cluster(name, kubeconfig, version)
                time.sleep(1)
                logger.info('Created cluster')
            except Exception as e:
                logger.warning(
                    "%s happened when restarting cluster, retrying...", e)
                retry_count -= 1
                if retry_count == 0:
                    raise e
                continue
            break

    def get_node_list(self, name: str):
        '''Fetch the name of worker nodes inside a cluster
        Args:
            1. name: name of the cluster name
        '''
        logger = get_thread_logger(with_prefix=False)

        cmd = ['docker', 'ps', '--format', '{{.Names}}', '-f']

        if name == None:
            cmd.append(f"name={CONST.CLUSTER_NAME}")
        else:
            cmd.append(f"name={name}")

        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.stdout == None or p.stdout == '':
            # no nodes can be found, returning an empty array
            return []
        logger.debug("Container found:", p.stdout.strip().split('\n'))
        return p.stdout.strip().split('\n')
