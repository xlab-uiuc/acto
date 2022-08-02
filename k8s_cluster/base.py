class KubernetesCluster(object):
    def configure_cluster(self, num_nodes: int, version: str):
        pass

    def get_context_name(self, cluster_name: str) -> str:
        pass

    def create_cluster(self, name: str, config: str, version: str):
        pass

    def load_images(self, images_archive_path: str, name: str):
        pass

    def delete_cluster(self, name: str):
        pass
