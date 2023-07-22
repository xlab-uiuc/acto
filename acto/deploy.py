from enum import auto, unique
from functools import wraps, partial
from typing import TypeVar, Callable

import yaml
from strenum import StrEnum

import acto.utils as utils
from acto.checker.checker_set import CheckerSet
from acto.checker.impl.health import HealthChecker
from acto.common import *
from acto.constant import CONST
from acto.input import InputModel
from acto.runner.runner import Runner
from acto.runner.snapshot_collector import CollectorContext, with_context, snapshot_collector
from acto.runner.trial import Trial, TrialInputIterator
from acto.utils import get_thread_logger, add_acto_label

CONST = CONST()
Snapshot = TypeVar('Snapshot')


@unique
class DeployMethod(StrEnum):
    HELM = auto()
    YAML = auto()
    KUSTOMIZE = auto()


class Deploy:
    """Class for different deploying methods

    TODO: @Tyler: This class needs to be refactored.
            The deploy is better to be stateful, storing the kubernetes client and kubectl client
            Currently the context and kubeconfig are passed to each method.
            The `kubectl` function is currently copied to this file temporarily,
                the plan is to switch to use the KubectlClient class
    """

    def __init__(self, file_path: str, init_yaml=None):
        self.crd_yaml_files = list(yaml.safe_load_all(open(file_path, 'r').read()))
        self.init_yaml_files = list(yaml.safe_load_all(open(init_yaml, 'r').read())) if init_yaml else None
        self.wait = 20  # sec

    def deploy(self, runner: Runner) -> str:
        # Return the namespace of the deployed operator
        # XXX: context param is temporary, need to figure out why rabbitmq complains about namespace
        pass

    def deploy_with_retry(self, runner: Runner, retry_count=3):
        logger = get_thread_logger(with_prefix=False)
        while retry_count > 0:
            try:
                return self.deploy(runner)
            except Exception as e:
                logger.warning(e)
                logger.info(
                    "deploy() failed. Double wait = " + str(self.wait))
                self.wait = self.wait * 2
                retry_count -= 1
        return False

    def check_status(self, runner: Runner):
        """
        We need to make sure operator to be ready before applying test cases, because Acto would
        crash later when running oracle if operator hasn't been ready
        """
        collector_context = CollectorContext(namespace='kube-system', timeout=self.wait)
        kube_snapshot_collector = partial(with_context(collector_context, snapshot_collector), ignore_cli_error=True)
        trial = Trial(TrialInputIterator.__new__(TrialInputIterator), CheckerSet({}, InputModel.__new__(InputModel), []))

        for i in range(5):
            kube_snapshot = kube_snapshot_collector(runner, trial, {
                'apiVersion': 'v1',
                'items': [],
                'kind': 'List'
            })
            health_result = HealthChecker().check(kube_snapshot, kube_snapshot)
            if health_result.means_ok():
                return True
        return False

    def chain_with(self, collector: Callable[[str, 'Runner', Trial, dict], Snapshot]) -> Callable[['Runner', Trial, dict], Snapshot]:
        cluster_setup = False

        @wraps(collector)
        def wrapper(runner: Runner, trial: Trial, context: dict) -> Snapshot:
            nonlocal cluster_setup
            namespace = None
            if not cluster_setup:
                namespace = self.deploy(runner)
                add_acto_label(runner.kubectl_client.api_client, namespace)
                cluster_setup = True
            return collector(namespace, runner, trial, context)

        return wrapper


#
# class Helm(Deploy):
#
#     def deploy(self, context: dict, context_name: str) -> bool:
#         logger = get_thread_logger(with_prefix=False)
#
#         context['namespace'] = CONST.ACTO_NAMESPACE
#         if self.init_yaml:
#             kubectl(['apply', '--server-side', '-f',
#                      self.init_yaml], context_name)
#         helm(['dependency', 'build', self.path], context_name)
#         helm([
#             'install', 'acto-test-operator', '--create-namespace', self.path, '--wait', '--timeout',
#             '3m', '-n', context['namespace']
#         ], context_name)
#
#         # use a counter to wait for 2 min (thus 24 below, since each wait is 5s)
#         counter = 0
#         while not self.check_status(context, context_name):
#             if counter > 24:
#                 logger.fatal(
#                     'Helm chart deployment failed to be ready within timeout')
#                 return False
#             time.sleep(5)
#
#         # TODO: Return True if deploy successfully
#         return True
#
#     def check_status(self, context, context_name: str) -> bool:
#         logger = get_thread_logger(with_prefix=False)
#
#         helm_ls_result = helm(
#             ['list', '-o', 'json', '--all-namespaces', '--all'], context_name)
#         try:
#             helm_release = json.loads(helm_ls_result.stdout)[0]
#         except Exception as e:
#             logger.error('Failed to get helm chart\'s status: %s' % e)
#             quit()
#
#         if helm_release["status"] != "deployed":
#             return False
#         else:
#             return True


class YamlDeploy(Deploy):

    def deploy(self, runner: Runner) -> str:
        # TODO: We cannot specify namespace ACTO_NAMESPACE here.
        # rabbitMQ operator will report the error message
        """
           the namespace from the provided object "rabbitmq-system" does not
           match the namespace "acto-namespace". You must pass '--namespace=rabbitmq-system' to perform this operation.
        """
        logger = get_thread_logger(with_prefix=True)
        print_event('Deploying operator...')

        kubectl_client = runner.kubectl_client

        namespace = utils.get_yaml_existing_namespace(self.crd_yaml_files) or CONST.ACTO_NAMESPACE
        ret = utils.create_namespace(kubectl_client.api_client, namespace)
        if ret is None:
            logger.critical('Failed to create namespace')
        # use server side apply to avoid last-applied-configuration
        if self.init_yaml_files:
            kubectl_client.apply(self.init_yaml_files, server_side=None)
            self.check_status(runner)
        kubectl_client.apply(self.crd_yaml_files, namespace=namespace, server_side=None)
        self.check_status(runner)
        print_event('Operator deployed')
        return namespace

#
# class Kustomize(Deploy):
#
#     def deploy(self, context, kubeconfig, context_name):
#         # TODO: We need to remove hardcoded namespace.
#         namespace = "cass-operator"
#         context['namespace'] = namespace
#         if self.init_yaml:
#             kubectl(['apply', '--server-side', '-f', self.init_yaml], kubeconfig=kubeconfig,
#                     context_name=context_name)
#         self.check_status(context, kubeconfig=kubeconfig, context_name=context_name)
#         kubectl(['apply', '--server-side', '-k', self.path, '-n', context['namespace']], kubeconfig=kubeconfig,
#                 context_name=context_name)
#         self.check_status(context, kubeconfig=kubeconfig, context_name=context_name)
#         return True
