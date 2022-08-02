class KubernetesCluster(object):
    def configure_cluster(num_workers: int):
        pass

    def get_context_name(cluster_name: str) -> str:
        pass

    def create_cluster(name: str, config: str, version: str):
        pass

    def load_images(images_archive_path: str, name: str):
        pass

    def delete_cluster(name: str):
        pass
