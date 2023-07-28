import logging
import os
import hashlib
import subprocess
import traceback
import uuid
from typing import Type, TypeVar, Callable, List

# this is a side effect import
import acto.monkey_patch.monkey_patch
from acto import ray_acto as ray
from acto.kubectl_client import KubectlClient
from acto.kubernetes_engine.base import KubernetesEngine
from acto.runner.trial import Trial
from filelock import FileLock

Engine = TypeVar('Engine', bound=KubernetesEngine)
Snapshot = TypeVar('Snapshot')


def hash_preload_images(preload_images: List[str]) -> str:
    preload_images = sorted(preload_images)
    m = hashlib.sha1()
    for image in preload_images:
        m.update(image.encode('ascii'))
    return m.hexdigest()


@ray.remote(scheduling_strategy="SPREAD", num_cpus=0, resources={"disk": 20})
class Runner:

    def __init__(self, engine_class: Type[Engine], engine_version: str, num_nodes: int,
                 preload_images: List[str] = None, preload_images_store: Callable[[str], str] = None):
        if preload_images_store is None:
            preload_images_store = lambda image_hash: f'/tmp/acto_image_{image_hash}.tar'
        preload_images_store = preload_images_store(hash_preload_images(preload_images))
        self.cluster_name = None
        self.preload_images = preload_images
        self.preload_images_store = preload_images_store
        self.kubernetes_engine_class = engine_class
        self.engine_version = engine_version
        self.num_nodes = num_nodes

    def run(self, trial: Trial, snapshot_collector: Callable[['Runner', Trial, dict], Snapshot]) -> Trial:
        '''This method uses the snapshot_collector to execute the trial
        '''
        self.setup_cluster()
        for system_input in trial:
            snapshot = None
            error = None
            try:
                snapshot = snapshot_collector(self, trial, system_input)
            except Exception as e:
                error = e
                # TODO: do not use print
                print(traceback.format_exc())
            trial.send_snapshot(snapshot, error)
        self.teardown_cluster()
        return trial

    def setup_cluster(self):
        self.cluster_name = str(uuid.uuid4())
        kube_dir = os.path.join(os.path.expanduser('~'), '.kube')
        os.makedirs(kube_dir, exist_ok=True)

        self.prefetch_image()

        self.cluster = self.kubernetes_engine_class()
        self.cluster.configure_cluster(self.num_nodes, self.engine_version)
        context_name = self.cluster.get_context_name(self.cluster_name)
        kubeconfig = os.path.join(kube_dir, context_name)
        self.cluster.create_cluster(self.cluster_name, kubeconfig, self.engine_version)

        if self.preload_images:
            self.cluster.load_images(self.preload_images_store, self.cluster_name)

        self.kubectl_client = KubectlClient(kubeconfig, context_name)

    def prefetch_image(self):
        if not self.preload_images:
            return
        lock_path = self.preload_images_store + '.lock'
        lock = FileLock(lock_path)
        with lock:
            if os.path.exists(self.preload_images_store):
                return
            logging.info('Creating preload images archive')
            # first make sure images are present locally
            for image in self.preload_images:
                subprocess.run(['docker', 'pull', image], stdout=subprocess.DEVNULL)
            subprocess.run(['docker', 'image', 'save', '-o', self.preload_images_store] +
                           list(self.preload_images), stdout=subprocess.DEVNULL)

    def teardown_cluster(self):
        self.cluster.delete_cluster(self.cluster_name, self.kubectl_client.kubeconfig)
        self.cluster_name = None
        try:
            os.remove(self.kubectl_client.kubeconfig)
        except OSError:
            pass
