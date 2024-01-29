"""Integration tests for Kubernetes system state collection."""
import os
import pathlib
import tempfile
import unittest

from acto.common import kubernetes_client
from acto.kubernetes_engine import kind
from acto.system_state.kubernetes_system_state import KubernetesSystemState

test_dir = pathlib.Path(__file__).parent.resolve()
test_data_dir = os.path.join(test_dir, "test_data")


class TestKubernetesSystemState(unittest.TestCase):
    """test Kubernetes system state collection."""

    def setUp(self):
        config_path = os.path.join(os.path.expanduser("~"), ".kube/test-config")
        name = "test-cluster"
        num_nodes = 1
        version = "v1.26.0"

        cluster_instance = kind.Kind(acto_namespace=0)

        cluster_instance.configure_cluster(num_nodes, version)
        print(
            f"Creating cluster {name} with {num_nodes} nodes, version {version}, "
            + f"configPath {config_path}"
        )
        cluster_instance.create_cluster(name, config_path)

        self.kubeconfig = config_path
        self.cluster_name = name
        self.cluster_instance = cluster_instance

    def tearDown(self):
        self.cluster_instance.delete_cluster(self.cluster_name, self.kubeconfig)

    def test_collect_and_serialization(self):
        """Test collect and serialization of Kubernetes system state."""

        api_client = kubernetes_client(
            self.kubeconfig,
            self.cluster_instance.get_context_name(self.cluster_name),
        )

        # check collection works
        state = KubernetesSystemState.from_api_client(api_client, "kube-system")
        assert "kindnet" in state.daemon_set
        assert "kube-proxy" in state.daemon_set
        assert "coredns" in state.deployment
        assert "kube-dns" in state.service
        assert "standard" in state.storage_class
        assert "coredns" in state.config_map
        assert "admin" in state.cluster_role
        assert "cluster-admin" in state.cluster_role_binding

        # check serialization works
        with tempfile.TemporaryFile("w") as file:
            state.dump(file)


if __name__ == "__main__":
    unittest.main()
