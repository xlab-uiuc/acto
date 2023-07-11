import os
import threading
import traceback
import uuid
from typing import Type, TypeVar, Callable

import ray

from acto.kubectl_client import KubectlClient
from acto.kubernetes_engine.base import KubernetesEngine
from acto.runner.trial import Trial

Engine = TypeVar('Engine', bound=KubernetesEngine)
Snapshot = TypeVar('Snapshot')


@ray.remote
class Runner:

    def __init__(self, engine_class: Type[Engine], engine_version: str, num_nodes: int):
        self.kubernetes_engine_class = engine_class
        self.engine_version = engine_version
        self.num_nodes = num_nodes
        self.cluster_ok_event: threading.Event = threading.Event()
        threading.Thread(target=self.__setup_cluster_and_set_available).start()

    def run(self, trial: Trial, snapshot_collector: Callable[['Runner', Trial, dict], Snapshot]) -> Trial:
        self.cluster_ok_event.wait()
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
        self.cluster_ok_event.clear()
        threading.Thread(target=self.__reset_cluster_and_set_available).start()
        return trial

    def __reset_cluster_and_set_available(self):
        self.__teardown_cluster()
        self.__setup_cluster()
        self.cluster_ok_event.set()

    def __setup_cluster_and_set_available(self):
        self.__setup_cluster()
        self.cluster_ok_event.set()

    def __setup_cluster(self):
        self.cluster_name = str(uuid.uuid4())
        kube_dir = os.path.join(os.path.expanduser('~'), '.kube')
        os.makedirs(kube_dir, exist_ok=True)

        self.cluster = self.kubernetes_engine_class()
        self.cluster.configure_cluster(self.num_nodes, self.engine_version)
        context_name = self.cluster.get_context_name(self.cluster_name)
        kubeconfig = os.path.join(kube_dir, context_name)
        self.cluster.create_cluster(self.cluster_name, kubeconfig, self.engine_version)

        self.kubectl_client = KubectlClient(kubeconfig, context_name)

    def __teardown_cluster(self):
        self.cluster.delete_cluster(self.cluster_name, self.kubectl_client.kubeconfig)
        self.cluster_name = None
        os.remove(self.kubectl_client.kubeconfig)
