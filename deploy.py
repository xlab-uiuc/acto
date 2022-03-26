from enum import Enum, auto, unique
from rich.console import Console
import constant
import sh
import json
import exception
import time


@unique
class DeployMethod(Enum):
    HELM = auto()
    YAML = auto()


class Deploy:
    def __init__(self, path: str, context, init_yaml):
        self.path = path
        self.context = context
        self.init_yaml = init_yaml
        self.console = Console()

    def deploy(self):
        pass

    def check_status(self):
        time.sleep(60)


class Helm(Deploy):
    def __init__(
            self,
            deploy_method: DeployMethod,
            path: str,
            context,
            init_yaml):
        if deploy_method is DeployMethod.HELM:
            super().__init__(path, context, init_yaml)
        else:
            raise exception.UnknownDeployMethodError

    def deploy(self):
        if self.init_yaml:
            sh.kubectl("apply", filename=self.init_yaml)

        sh.helm("dependency", "build", self.path)
        sh.helm(
            "install",
            "acto-test-operator",
            "--create-namespace",
            self.path,
            wait=True,
            timeout="3m",
            namespace=constant.ACTO_NAMESPACE)

        self.check_status()

    def check_status(self):
        helm_ls_result = sh.helm("ls", o="json", all_namespaces=True, all=True)
        try:
            helm_release = json.loads(helm_ls_result.stdout)[0]
        except Exception:
            self.console.log(
                "Failed to get helm chart's status",
                style="bold red")
            quit()

        if helm_release["status"] != "deployed":
            self.console.log(
                "Helm chart deployment failed to be ready within timeout",
                style="bold red")
            raise Exception


class Yaml(Deploy):
    def __init__(
            self,
            deploy_method: DeployMethod,
            path: str,
            context,
            init_yaml):
        if deploy_method is DeployMethod.YAML:
            super().__init__(path, context, init_yaml)
        else:
            raise exception.UnknownDeployMethodError

    def deploy(self):
        if self.init_yaml:
            sh.kubectl("apply", filename=self.init_yaml)
        sh.kubectl("apply", filename=self.path)
        super().check_status()

    # TODO: Do we need to check operator's status?
    # Even if the operator gets ready after the custom resource is created,
    # the custom resource event will not be lost.

    # If we actually need to check operator's status, we have other solutions.
    # Ex: Wait for 30 seconds, and then wait until every Pod is running.

    def check_status(self):
        pass
