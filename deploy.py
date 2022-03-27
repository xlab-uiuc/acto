from enum import Enum, auto, unique
from rich.console import Console
from constant import CONST
import sh
import json
import exception
import time
import logging
from kubernetes.client import AppsV1Api
from k8s_helper import get_deployment_available_status, get_stateful_set_available_status, get_yaml_existing_namespace

CONST = CONST()

@unique
class DeployMethod(Enum):
    HELM = auto()
    YAML = auto()


class Deploy:
    def __init__(self, deploy_method: DeployMethod, path: str, context: dict, init_yaml = None):
        self.path = path
        self.init_yaml = init_yaml
        self.console = Console()
        self.deploy_method = deploy_method
        self.context = context
        self.appsV1api = AppsV1Api()

    def deploy(self):
        pass

    def check_status(self):
        time.sleep(60)

    def new(self):
        if self.deploy_method is DeployMethod.HELM:
            return Helm(self.deploy_method, self.path, self.context, self.init_yaml)
        elif self.deploy_method is DeployMethod.YAML:
            return Yaml(self.deploy_method, self.path, self.context, self.init_yaml)
        else:
            raise exception.UnknownDeployMethodError 

class Helm(Deploy):
    def deploy(self):
        if self.init_yaml:
            sh.kubectl("apply", filename=self.init_yaml, namespace=CONST.ACTO_NAMESPACE)
        self.context['namespace'] = CONST.ACTO_NAMESPACE
        sh.helm("dependency", "build", self.path)
        sh.helm(
            "install",
            "acto-test-operator",
            "--create-namespace",
            self.path,
            wait=True,
            timeout="3m",
            namespace=CONST.ACTO_NAMESPACE)

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
    def deploy(self):
        # TODO: We cannot specify namespace ACTO_NAMESPACE here.
        # rabbitMQ operator will report the error message
        '''
           the namespace from the provided object "rabbitmq-system" does not 
           match the namespace "acto-namespace". You must pass '--namespace=rabbitmq-system' to perform this operation.
        '''
        namespace = get_yaml_existing_namespace(self.path) or CONST.ACTO_NAMESPACE
        self.context['namespace'] = namespace
        if self.init_yaml:
            sh.kubectl("apply", filename=
                self.init_yaml, namespace=namespace)
        sh.kubectl("apply", filename=
            self.path, namespace=namespace)
        super().check_status()

    # TODO: Do we need to check operator's status?
    # Even if the operator gets ready after the custom resource is created,
    # the custom resource event will not be lost.

    # If we actually need to check operator's status, we have other solutions.
    # Ex: Wait for 30 seconds, and then wait until every Pod is running.

    def check_status(self):
        logging.debug('Deploying the operator, waiting for it to be ready')
        pod_ready = False
        operator_stateful_states = []
        for tick in range(90):
            # get all deployment and stateful set.
            operator_deployments = self.appv1Api.list_namespaced_deployment(
                self.context['namespace'],
                watch=False).items
            operator_stateful_states = self.appv1Api.list_namespaced_stateful_set(
                self.context['namespace'],
                watch=False).items
            # TODO: we should check all deployment and stateful set are ready
            operator_deployments_is_ready = len(operator_deployments) >= 1 \
                    and get_deployment_available_status(operator_deployments[0])
            operator_stateful_states_is_ready = len(operator_stateful_states) >= 1 \
                    and get_stateful_set_available_status(operator_stateful_states[0])
            if operator_deployments_is_ready or operator_stateful_states_is_ready:
                logging.debug('Operator ready')
                pod_ready = True
                break
            time.sleep(1)
        logging.info('Operator took %d seconds to get ready' % tick)
        if not pod_ready:
            logging.error("operator deployment failed to be ready within timeout")
            return False
        else:
            return True

# Example:
# if __name__ == '__main__':
#     deploy = Deploy(DeployMethod.YAML, "data/rabbitmq-operator/operator.yaml").new()
#     deploy.deploy()

#     deploy1 = Deploy(DeployMethod.HELM, "data/mongodb-operator/community-operator/").new()
#     deploy1.deploy()
