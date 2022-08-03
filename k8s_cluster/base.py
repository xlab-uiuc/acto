import subprocess
import logging
import time
import kubernetes

from constant import CONST


class KubernetesCluster(object):
    def configure_cluster(self, num_nodes: int, version: str):
        pass

    def get_context_name(self, cluster_name: str) -> str:
        pass

    def create_cluster(self, name: str, version: str):
        pass

    def load_images(self, images_archive_path: str, name: str):
        pass

    def delete_cluster(self, name: str):
        pass

    def restart_cluster(self, name: str, version: str):
        self.delete_cluster(name)
        time.sleep(1)
        self.create_cluster(name, version)
        time.sleep(1)
        logging.info('Created cluster')

    def get_node_list(self, name: str):
        '''Fetch the name of worker nodes inside a cluster
        Args:
            1. name: name of the cluster name
        '''
        cmd = ['docker', 'ps', '--format', '{{.Names}}', '-f']

        if name == None:
            cmd.append(f"name={CONST.CLUSTER_NAME}")
        else:
            cmd.append(f"name={name}")

        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.stdout == None or p.stdout == '':
            # no nodes can be found, returning an empty array
            return []
        print("Container found:", p.stdout.strip().split('\n'))
        return p.stdout.strip().split('\n')
