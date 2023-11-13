import os

import pytest

from acto.kubernetes_engine.base import KubernetesEngine
from acto.kubernetes_engine.kind import Kind

from . import minikube as minikube

# class TestKubernetesEngines():
#     kind_cluster = kind.Kind(acto_namespace=0)

kind_cluster = Kind(acto_namespace=0)
# minikube_cluster = minikube.Minikube(acto_namespace=0)

testcases = [(kind_cluster,3, "v1.27.3")]

@pytest.mark.kubernetes_engine
@pytest.mark.parametrize('cluster_instance,num_nodes,version', testcases)
def test_kubernetes_engines(cluster_instance: KubernetesEngine, num_nodes, version):
    configPath = os.path.join(os.path.expanduser('~'), '.kube/test-config')
    name = "test-cluster"
    # num_nodes = 3
    # version = "v1.27.4"

    cluster_instance.configure_cluster(num_nodes, version)
    print(
        f"Creating cluster {name} with {num_nodes} nodes, version {version}, configPath {configPath}")
    cluster_instance.create_cluster(name, configPath)

    node_list = cluster_instance.get_node_list(name)
    assert len(node_list) == num_nodes

    cluster_instance.delete_cluster(name, configPath)
    with pytest.raises(RuntimeError):
        # expect to raise RuntimeError
        # get_node_list should raise RuntimeError when cluster is not found
        cluster_instance.get_node_list(name)


    # def test_minikube_load_image():
    #     num_nodes = 3
    #     name = "hz"
    #     version = "v1.27.4"
    #     cluster = minikube.Minikube(acto_namespace = 0, num_nodes=num_nodes, version=version)
    #     # cluster.create_cluster(name, "/users/hzeng21/.kube/config2")
    #     cluster.load_images("/users/hzeng21/.kube/sleepy.tar", name=name)