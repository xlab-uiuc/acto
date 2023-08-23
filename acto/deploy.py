import json
import time

import kubernetes

import acto.exception
from acto.lib.operator_config import DeployMethod
import acto.utils as utils
from acto.common import *
from acto.constant import CONST
from acto.utils import get_thread_logger
from acto.utils.preprocess import add_acto_label

CONST = CONST()


class Deploy:

    '''Class for different deploying methods

    TODO: @Tyler: This class needs to be refactored. 
            The deploy is better to be stateful, storing the kubernetes client and kubectl client
            Currently the context and kubeconfig are passed to each method.
            The `kubectl` function is currently copied to this file temporarily,
                the plan is to switch to use the KubectlClient class
    '''

    def __init__(self, deploy_method: DeployMethod, path: str, init_yaml=None):
        self.path = path
        self.init_yaml = init_yaml
        self.deploy_method = deploy_method
        self.wait = 20  # sec

    def undeploy(self, context: dict, apiclient):
        logger = get_thread_logger(with_prefix=False)
        corev1Api = kubernetes.client.CoreV1Api(apiclient)
        try:
            corev1Api.delete_namespace(name=context['namespace'])
        except Exception as e:
            logger.error(e)

        while True:
            nss = corev1Api.list_namespace().items
            for ns in nss:
                if ns.metadata.name == context['namespace']:
                    logger.info('Namespace %s still exists' %
                                context['namespace'])
                    time.sleep(5)
                    continue
            break
        time.sleep(5)
        logger.info('Namespace %s deleted' % context['namespace'])

    def deploy(self, context: dict, kubeconfig: str, context_name: str):
        # XXX: context param is temporary, need to figure out why rabbitmq complains about namespace
        pass

    def deploy_with_retry(self, context, kubeconfig: str, context_name: str, retry_count=3):
        logger = get_thread_logger(with_prefix=False)
        while retry_count > 0:
            try:
                return self.deploy(context, kubeconfig, context_name)
            except Exception as e:
                logger.warn(e)
                logger.info(
                    "deploy() failed. Double wait = " + str(self.wait))
                self.wait = self.wait * 2
                retry_count -= 1
        return False

    def check_status(self, context: dict, kubeconfig: str, context_name: str):
        '''

        We need to make sure operator to be ready before applying test cases, because Acto would
        crash later when running oracle if operator hasn't been ready
        '''
        logger = get_thread_logger(with_prefix=False)

        apiclient = kubernetes_client(kubeconfig, context_name)

        logger.debug('Waiting for all pods to be ready')
        time.sleep(10)
        pod_ready = False
        for tick in range(600):
            # check if all pods are ready
            pods = kubernetes.client.CoreV1Api(
                apiclient).list_pod_for_all_namespaces().items

            all_pods_ready = True
            for pod in pods:
                if pod.status.phase == 'Succeeded':
                    continue
                if not utils.is_pod_ready(pod):
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
            raise acto.exception.UnknownDeployMethodError


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

    def deploy(self, context: dict, kubeconfig: str, context_name: str):
        # TODO: We cannot specify namespace ACTO_NAMESPACE here.
        # rabbitMQ operator will report the error message
        '''
           the namespace from the provided object "rabbitmq-system" does not 
           match the namespace "acto-namespace". You must pass '--namespace=rabbitmq-system' to perform this operation.
        '''
        logger = get_thread_logger(with_prefix=True)
        print_event('Deploying operator...')

        namespace = utils.get_yaml_existing_namespace(
            self.path) or CONST.ACTO_NAMESPACE
        context['namespace'] = namespace
        ret = utils.create_namespace(
            kubernetes_client(kubeconfig, context_name), namespace)
        if ret == None:
            logger.error('Failed to create namespace')
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f', self.init_yaml], kubeconfig=kubeconfig,
                    context_name=context_name)
        self.check_status(context, kubeconfig=kubeconfig,
                          context_name=context_name)
        kubectl(['apply', '--server-side', '-f', self.path, '-n', context['namespace']], kubeconfig=kubeconfig,
                context_name=context_name)
        self.check_status(context, kubeconfig=kubeconfig,
                          context_name=context_name)
        add_acto_label(kubernetes_client(kubeconfig, context_name), context)
        self.check_status(context, kubeconfig=kubeconfig,
                          context_name=context_name)
        time.sleep(20)

        # TODO: Return True if deploy successfully
        print_event('Operator deployed')
        return True


class Kustomize(Deploy):

    def deploy(self, context, kubeconfig, context_name):
        # TODO: We need to remove hardcoded namespace.
        namespace = "cass-operator"
        context['namespace'] = namespace
        if self.init_yaml:
            kubectl(['apply', '--server-side', '-f', self.init_yaml], kubeconfig=kubeconfig,
                    context_name=context_name)
        self.check_status(context, kubeconfig=kubeconfig,
                          context_name=context_name)
        kubectl(['apply', '--server-side', '-k', self.path, '-n', context['namespace']], kubeconfig=kubeconfig,
                context_name=context_name)
        self.check_status(context, kubeconfig=kubeconfig,
                          context_name=context_name)
        return True


def kubectl(args: list,
            kubeconfig: str,
            context_name: str,
            capture_output=False,
            text=False) -> subprocess.CompletedProcess:
    logger = get_thread_logger(with_prefix=True)

    cmd = ['kubectl']
    cmd.extend(args)

    if kubeconfig:
        cmd.extend(['--kubeconfig', kubeconfig])
    else:
        raise Exception('Kubeconfig is not set')

    if context_name == None:
        logger.error('Missing context name for kubectl')
    cmd.extend(['--context', context_name])

    if capture_output:
        p = subprocess.run(cmd, capture_output=capture_output, text=text)
    else:
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL)
    return p
