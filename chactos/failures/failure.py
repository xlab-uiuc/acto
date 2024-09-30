import abc
import os

import yaml

from acto.kubectl_client.kubectl import KubectlClient
from acto.utils import thread_logger

FAILURE_DIR = ".failures"


class Failure(abc.ABC):
    """Abstract base class for failures"""

    def __init__(self):
        os.makedirs(FAILURE_DIR, exist_ok=True)

    def apply(self, kubectl_client: KubectlClient):
        """Apply the failure to the cluster"""
        logger = thread_logger.get_thread_logger()
        logger.info("Applying %s...", self.name())
        failure_file = os.path.join(FAILURE_DIR, self.name() + ".yaml")
        self.to_file(failure_file)
        p = kubectl_client.kubectl(
            ["apply", "-f", failure_file, "-n", "chaos-mesh"],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            raise RuntimeError(f"Failed to apply {self.name()}: {p.stderr}")
        p = kubectl_client.wait(
            failure_file,
            'jsonpath={.status.conditions[?(@.type=="AllInjected")].status}=True',
            timeout=10,
            namespace="chaos-mesh",
        )
        # FIXME: We are continuing execution if network chaos failed to select
        # the pods currently (09/26) the only reason is that the pods are gone
        #  (like when testing steopped: true).
        # Is this the only case that we can skip??
        if p.returncode != 0:
            logger.warning(
                "Fault injection failed to be applied in 10 seconds."
            )
        logger.info("%s failure applied", self.name())

    def cleanup(self, kubectl_client: KubectlClient):
        """Cleanup the failure from the cluster"""
        failure_file = os.path.join(FAILURE_DIR, self.name() + ".yaml")
        p = kubectl_client.kubectl(
            ["delete", "-f", failure_file, "-n", "chaos-mesh", "--timeout=30s"],
            capture_output=True,
        )
        if p.returncode != 0:
            thread_logger.get_thread_logger().error(
                "Failed to delete %s: %s", self.name(), p.stderr
            )
        thread_logger.get_thread_logger().info(
            "%s failure cleaned up", self.name()
        )

    @abc.abstractmethod
    def name(self) -> str:
        """Get the name of the failure"""
        raise NotImplementedError

    @abc.abstractmethod
    def to_dict(self) -> dict:
        """Dump the spec to a dict"""
        raise NotImplementedError

    def to_file(self, file_path: str):
        """Dump the spec to a file"""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)
