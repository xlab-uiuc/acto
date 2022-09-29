from enum import Enum, auto, unique
from constant import CONST
import json
import exception
import time

import k8s_helper
from common import *
from thread_logger import get_thread_logger

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
        self.deploy_method = deploy_method
        self.wait = 20  # sec

    def deploy(self, context: dict, context_name: str):
        # XXX: context param is temporary, need to figure out why rabbitmq complains about namespace
        pass

    def deploy_with_retry(self, context, context_name: str, retry_count=3):
        logger = get_thread_logger(with_prefix=False)
        while retry_count > 0:
            try:
                return self.deploy(context, context_name)
            except Exception as e:
                logger.warn(e)
                logger.info(
                    "deploy() failed. Double wait = " + str(self.wait))
                self.wait = self.wait * 2
                retry_count -= 1
        return False

    def check_status(self, context: dict, context_name: str):
        '''

        We need to make sure operator to be ready before applying test cases, because Acto would
        crash later when running oracle if operator hasn't been ready
        '''
        logger = get_thread_logger(with_prefix=False)

        apiclient = kubernetes_client(context_name)

        logger.debug('Waiting for all pods to be ready')
        pod_ready = False
        for tick in range(600):
            # check if all pods are ready
            pods = kubernetes.client.CoreV1Api(
                apiclient).list_pod_for_all_namespaces().items

            all_pods_ready = True
            for pod in pods:
                if pod.status.phase == 'Succeeded':
                    continue
                if not k8s_helper.is_pod_ready(pod):
                    all_pods_ready = False

            if all_pods_ready:
                logger.info('Operator ready')
                pod_ready = True
                break

            time.sleep(5)
        logger.info('All pods took %d seconds to get ready' % (tick * 5))
        if not pod_ready:
            logger.error("Some pods failed to be ready within timeout")
            return False
        else:
            return True

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

    def deploy(self, context: dict, context_name: str) -> bool:
        logger = get_thread_logger(with_prefix=False)

        context['namespace'] = CONST.ACTO_NAMESPACE
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f',
                    self.init_yaml], context_name)
        helm(['dependency', 'build', self.path], context_name)
        helm([
            'install', 'acto-test-operator', '--create-namespace', self.path, '--wait', '--timeout',
            '3m', '-n', context['namespace']
        ], context_name)

        # use a counter to wait for 2 min (thus 24 below, since each wait is 5s)
        counter = 0
        while not self.check_status(context, context_name):
            if counter > 24:
                logger.fatal(
                    'Helm chart deployment failed to be ready within timeout')
                return False
            time.sleep(5)

        # TODO: Return True if deploy successfully
        return True

    def check_status(self, context, context_name: str) -> bool:
        logger = get_thread_logger(with_prefix=False)

        helm_ls_result = helm(
            ['list', '-o', 'json', '--all-namespaces', '--all'], context_name)
        try:
            helm_release = json.loads(helm_ls_result.stdout)[0]
        except Exception as e:
            logger.error('Failed to get helm chart\'s status: %s' % e)
            quit()

        if helm_release["status"] != "deployed":
            return False
        else:
            return True


class Yaml(Deploy):

    def deploy(self, context: dict, context_name: str):
        # TODO: We cannot specify namespace ACTO_NAMESPACE here.
        # rabbitMQ operator will report the error message
        '''
           the namespace from the provided object "rabbitmq-system" does not 
           match the namespace "acto-namespace". You must pass '--namespace=rabbitmq-system' to perform this operation.
        '''
        logger = get_thread_logger(with_prefix=True)

        namespace = k8s_helper.get_yaml_existing_namespace(
            self.path) or CONST.ACTO_NAMESPACE
        context['namespace'] = namespace
        ret = k8s_helper.create_namespace(
            kubernetes_client(context_name), namespace)
        if ret == None:
            logger.error('Failed to create namespace')
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f', self.init_yaml],
                    context_name)
        self.check_status(context, context_name)
        kubectl(['apply', '--server-side', '-f', self.path, '-n', context['namespace']],
                context_name)
        self.check_status(context, context_name)

        # TODO: Return True if deploy successfully
        return True


class Kustomize(Deploy):

    def deploy(self, context, context_name):
        # TODO: We need to remove hardcoded namespace.
        namespace = "cass-operator"
        context['namespace'] = namespace
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f', self.init_yaml],
                    context_name)
        self.check_status(context, context_name)
        kubectl(['apply', '--server-side', '-k', self.path, '-n', context['namespace']],
                context_name)
        self.check_status(context, context_name)
        return True


# Example:
# if __name__ == '__main__':
#     deploy = Deploy(DeployMethod.YAML, "data/rabbitmq-operator/operator.yaml").new()
#     deploy.deploy()

#     deploy1 = Deploy(DeployMethod.HELM, "data/mongodb-operator/community-operator/").new()
#     deploy1.deploy()
