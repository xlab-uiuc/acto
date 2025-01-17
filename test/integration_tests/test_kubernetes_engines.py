"""Test KubernetesEngine interface"""

import os

import pytest

# from acto.kubernetes_engine.base import KubernetesEngine
from acto.kubernetes_engine.base import KubernetesEngine
from acto.kubernetes_engine.kind import Kind
from acto.kubernetes_engine.minikube import Minikube
from acto.kubernetes_engine.provided import ProvidedKubernetesEngine
from acto.lib.operator_config import SelfProvidedKubernetesConfig

testcases = [("kind", 4, "v1.27.3")]


@pytest.mark.kubernetes_engine
@pytest.mark.parametrize("cluster_type,num_nodes,version", testcases)
def test_kubernetes_engines(cluster_type: str, num_nodes, version):
    """Test KubernetesEngine interface"""
    config_path = os.path.join(os.path.expanduser("~"), ".kube/test-config")
    name = "test-cluster"

    cluster_instance: KubernetesEngine
    if cluster_type == "kind":
        cluster_instance = Kind(
            acto_namespace=0, num_nodes=num_nodes, version=version
        )
    elif cluster_type == "minikube":
        cluster_instance = Minikube(
            acto_namespace=0, num_nodes=num_nodes, version=version
        )

    print(
        f"Creating cluster {name} with {num_nodes} nodes, version {version}, "
        + "configPath {config_path}"
    )
    cluster_instance.create_cluster(name, config_path)

    node_list = cluster_instance.get_node_list(name)
    assert len(node_list) == num_nodes + 1

    cluster_instance.delete_cluster(name, config_path)
    with pytest.raises(RuntimeError):
        # expect to raise RuntimeError
        # get_node_list should raise RuntimeError when cluster is not found
        cluster_instance.get_node_list(name)


@pytest.mark.kubernetes_engine
def test_user_provided_kubernetes():
    """Test creating a user provided kubernetes cluster from Kind"""
    config_path = os.path.join(os.path.expanduser("~"), ".kube/test-config")
    name = "test-cluster"
    cluster_instance = Kind(acto_namespace=0, num_nodes=1, version="v1.27.3")
    cluster_instance.restart_cluster(name, config_path)

    provided = ProvidedKubernetesEngine(
        acto_namespace=0,
        provided=SelfProvidedKubernetesConfig(
            kube_config=config_path,
            kube_context=cluster_instance.get_context_name(name),
        ),
    )
    provided.create_cluster(name, config_path)
