import kubernetes
import subprocess
import time
import logging
from deepdiff import DeepDiff

from common import RunResult


class Checker:
    pods = {}

    def __init__(self, namespace: str, cur_path: str, corev1, appv1) -> None:
        self.namespace = namespace
        self.cur_path = cur_path
        self.corev1 = corev1
        self.appv1 = appv1

    def check_resources(self):
        # Check pods
        current_pods = self.get_all_pods(self.namespace)
        diff = DeepDiff(self.pods, current_pods, ignore_order=True, report_repetition=True)
        logging.info(diff)
        self.pods = current_pods

    def run_and_check(self, cmd: list, generation: int) -> RunResult:
        '''Runs the cmd and check the result

        Args:
            cmd: list of cmd args
            metadata: dict of test run info
            generation: how many mutations have been run before

        Returns:
            result of the run
        '''
        cli_result = subprocess.run(cmd, capture_output=True, text=True)

        if cli_result.stdout.find('error') != -1 or cli_result.stderr.find(
                'error') != -1:
            logging.error('Invalid input, reject mutation')
            logging.error('STDOUT: ' + cli_result.stdout)
            logging.error('STDERR: ' + cli_result.stderr)
            return RunResult.invalidInput

        if cli_result.stdout.find('unchanged') != -1 or cli_result.stderr.find(
                'unchanged') != -1:
            logging.error('CR unchanged, continue')
            return RunResult.unchanged
        logging.error('STDOUT: ' + cli_result.stdout)
        logging.error('STDERR: ' + cli_result.stderr)
        time.sleep(150)

        log_result = self.check_log(generation)
        self.check_resources()

        return RunResult.passing


    def get_all_pods(self, namespace: str) -> dict:
        '''Get all pods in the application namespace
        
        Returns
            dict of all pods
        '''
        pods_dict = {}
        pods = self.corev1.list_namespaced_pod(namespace=namespace, watch=False).items
        for pod in pods:
            pods_dict[pod.metadata.name] = pod.to_dict()
        return pods_dict


    def get_all_stateful_sets(self, namespace: str) -> dict:
        sts_dict = {}
        sts = self.appv1.list_namespaced_stateful_set(namespace=namespace,
                                                watch=False).items
        for stateful_set in sts:
            sts_dict[stateful_set.metadata.name] = stateful_set.to_dict()
        return sts_dict


    def check_log(self, generation: int) -> RunResult:
        '''Check the operator log for error msg
        
        Returns
            RunResult of the checking
        '''
        operator_pod_list = self.corev1.list_namespaced_pod(
            namespace=self.namespace,
            watch=False,
            label_selector="testing/tag=operator-pod").items
        if len(operator_pod_list) >= 1:
            logging.debug('Got operator pod: pod name:' +
                        operator_pod_list[0].metadata.name)
        else:
            logging.error('Failed to find operator pod')

        log = self.corev1.read_namespaced_pod_log(
            name=operator_pod_list[0].metadata.name,
            namespace=self.namespace)

        with open(
                '%s/operator-%d.log' % (self.cur_path, generation),
                'w') as fout:
            fout.write(log)

        if log.find('error') != -1:
            logging.info('Found error in operator log')
            return RunResult.error

        return RunResult.passing