from enum import Enum, auto, unique
from rich.console import Console
from constant import CONST
import sh
import json
import exception
import time
import logging
from k8s_helper import get_yaml_existing_namespace, create_namespace
from time import sleep
from common import *

CONST = CONST()


@unique
class DeployMethod(Enum):
    HELM = auto()
    YAML = auto()
    KUSTOMIZE = auto()


class Deploy:

    def __init__(self, deploy_method: DeployMethod, path: str, init_yaml=None):
        self.path = path
        self.init_yaml = init_yaml
        self.console = Console()
        self.deploy_method = deploy_method
        self.wait = 10  # sec

    def deploy(self, context: dict, cluster_name: str):
        # XXX: context param is temporary, need to figure out why rabbitmq complains about namespace
        pass

    def deploy_with_retry(self, context, cluster_name: str, retry_count=3):
        while retry_count > 0:
            try:
                return self.deploy(context, cluster_name)
            except Exception as e:
                logging.warn(e)
                logging.info("deploy() failed. Double wait = " + str(self.wait))
                self.wait = self.wait * 2
                retry_count -= 1
        return False

    def check_status(self, cluster_name):
        time.sleep(10)

    def new(self):
        if self.deploy_method is DeployMethod.HELM:
            return Helm(self.deploy_method, self.path, self.init_yaml)
        elif self.deploy_method is DeployMethod.YAML:
            return Yaml(self.deploy_method, self.path, self.init_yaml)
        elif self.deploy_method is DeployMethod.KUSTOMIZE:
            return Kustomize(self.deploy_method, self.path, self.init_yaml)
        else:
            raise exception.UnknownDeployMethodError


class Helm(Deploy):

    def deploy(self, context: dict, cluster_name: str) -> bool:
        context['namespace'] = CONST.ACTO_NAMESPACE
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f', self.init_yaml], cluster_name)
        helm(['dependency', 'build', self.path], cluster_name)
        helm([
            'install', 'acto-test-operator', '--create-namespace', self.path, '--wait', '--timeout',
            '3m', '-n', context['namespace']
        ], cluster_name)

        counter = 0  # use a counter to wait for 2 min (thus 24 below, since each wait is 5s)
        while not self.check_status(cluster_name):
            if counter > 24:
                logging.fatal('Helm chart deployment failed to be ready within timeout')
                return False
            time.sleep(5)

        # TODO: Return True if deploy successfully
        return True

    def check_status(self, cluster_name: str) -> bool:
        helm_ls_result = helm(['list', '-o', 'json', '--all-namespaces', '--all'], cluster_name)
        try:
            helm_release = json.loads(helm_ls_result.stdout)[0]
        except Exception as e:
            logging.error('Failed to get helm chart\'s status: %s' % e)
            quit()

        if helm_release["status"] != "deployed":
            return False
        else:
            return True


class Yaml(Deploy):

    def deploy(self, context: dict, cluster_name: str):
        # TODO: We cannot specify namespace ACTO_NAMESPACE here.
        # rabbitMQ operator will report the error message
        '''
           the namespace from the provided object "rabbitmq-system" does not 
           match the namespace "acto-namespace". You must pass '--namespace=rabbitmq-system' to perform this operation.
        '''
        namespace = get_yaml_existing_namespace(self.path) or CONST.ACTO_NAMESPACE
        context['namespace'] = namespace
        ret = create_namespace(kubernetes_client(cluster_name), namespace)
        if ret == None:
            logging.error('Failed to create namespace')
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f', self.init_yaml],
                    cluster_name)
        kubectl(['apply', '--server-side', '-f', self.path, '-n', context['namespace']],
                cluster_name)
        super().check_status(cluster_name)

        # TODO: Return True if deploy successfully
        return True

    # TODO: Do we need to check operator's status?
    # Even if the operator gets ready after the custom resource is created,
    # the custom resource event will not be lost.

    # If we actually need to check operator's status, we have other solutions.
    # Ex: Wait for 30 seconds, and then wait until every Pod is running.

    # def check_status(self):
    #     logging.debug('Deploying the operator, waiting for it to be ready')
    #     pod_ready = False
    #     operator_stateful_states = []
    #     for tick in range(90):
    #         # get all deployment and stateful set.
    #         operator_deployments = self.appv1Api.list_namespaced_deployment(
    #             context['namespace'],
    #             watch=False).items
    #         operator_stateful_states = self.appv1Api.list_namespaced_stateful_set(
    #             context['namespace'],
    #             watch=False).items
    #         # TODO: we should check all deployment and stateful set are ready
    #         operator_deployments_is_ready = len(operator_deployments) >= 1 \
    #                 and get_deployment_available_status(operator_deployments[0])
    #         operator_stateful_states_is_ready = len(operator_stateful_states) >= 1 \
    #                 and get_stateful_set_available_status(operator_stateful_states[0])
    #         if operator_deployments_is_ready or operator_stateful_states_is_ready:
    #             logging.debug('Operator ready')
    #             pod_ready = True
    #             break
    #         time.sleep(1)
    #     logging.info('Operator took %d seconds to get ready' % tick)
    #     if not pod_ready:
    #         logging.error("operator deployment failed to be ready within timeout")
    #         return False
    #     else:
    #         return True


class Kustomize(Deploy):

    def deploy(self, context, cluster_name):
        # TODO: We need to remove hardcoded namespace.
        namespace = "cass-operator"
        context['namespace'] = namespace
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f', self.init_yaml],
                    cluster_name)
        sleep(self.wait)
        kubectl(['apply', '--server-side', '-k', self.path, '-n', context['namespace']],
                cluster_name)
        super().check_status(cluster_name)
        return True


# Example:
# if __name__ == '__main__':
#     deploy = Deploy(DeployMethod.YAML, "data/rabbitmq-operator/operator.yaml").new()
#     deploy.deploy()

#     deploy1 = Deploy(DeployMethod.HELM, "data/mongodb-operator/community-operator/").new()
#     deploy1.deploy()
