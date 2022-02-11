import subprocess
import time
import logging
from deepdiff import DeepDiff

from common import RunResult


class Checker:
    pods = {}
    stateful_sets = {}
    config_maps = {}
    services = {}
    customResource = {}

    def __init__(self, namespace: str, cur_path: str, corev1Api, appv1Api,
                 customObjectApi) -> None:
        self.namespace = namespace
        self.cur_path = cur_path
        self.corev1Api = corev1Api
        self.appv1Api = appv1Api
        self.customObjectApi = customObjectApi

    def check_resources(self, input_diff, generation: int):
        # TODO: Get this into a loop

        # Check pods
        current_pods = self.get_all_objects(self.corev1Api.list_namespaced_pod)
        pods_diff = DeepDiff(self.pods,
                             current_pods,
                             ignore_order=True,
                             report_repetition=True)
        self.pods = current_pods

        # Check statefulSets
        current_sts = self.get_all_objects(
            self.appv1Api.list_namespaced_stateful_set)
        sts_diff = DeepDiff(self.stateful_sets,
                            current_sts,
                            ignore_order=True,
                            report_repetition=True)
        self.stateful_sets = current_sts

        current_config_maps = self.get_all_objects(
            self.corev1Api.list_namespaced_config_map)
        config_maps_diff = DeepDiff(self.config_maps,
                                    current_config_maps,
                                    ignore_order=True,
                                    report_repetition=True)
        self.config_maps = current_config_maps

        current_services = self.get_all_objects(
            self.corev1Api.list_namespaced_service)
        services_diff = DeepDiff(self.services,
                                 current_services,
                                 ignore_order=True,
                                 report_repetition=True)
        self.services = current_services

        current_cr = self.get_custom_resources(self.namespace, 'rabbitmq.com',
                                               'v1beta1', 'rabbitmqclusters')
        logging.debug(current_cr)

        cr_diff = DeepDiff(self.customResource,
                           current_cr,
                           ignore_order=True,
                           report_repetition=True)
        self.customResource = current_cr

        with open('%s/delta-%d.log' % (self.cur_path, generation),
                  'w') as fout:
            fout.write('----- Input Delta -----\n')
            fout.write(str(input_diff.to_dict()))
            fout.write('\n----- Pods Delta -----\n')
            fout.write(str(pods_diff.to_dict()))
            fout.write('\n----- Sts Delta -----\n')
            fout.write(str(sts_diff.to_dict()))
            fout.write('\n----- Config Map Delta -----\n')
            fout.write(str(config_maps_diff.to_dict()))
            fout.write('\n----- Services Delta -----\n')
            fout.write(str(services_diff.to_dict()))
            fout.write('\n----- CR Delta -----\n')
            fout.write(str(cr_diff.to_dict()))

    def run_and_check(self, cmd: list, input_diff,
                      generation: int) -> RunResult:
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
        logging.debug('STDOUT: ' + cli_result.stdout)
        logging.debug('STDERR: ' + cli_result.stderr)

        wait_duration = 180
        logging.info('Wait for %d seconds' % wait_duration)
        time.sleep(wait_duration)

        self.check_resources(input_diff, generation)

        return self.check_log(generation)

    def get_all_objects(self, method) -> dict:
        '''Get all pods in the application namespace
        
        Returns
            dict of all pods
        '''
        result_dict = {}
        resource_objects = method(namespace=self.namespace, watch=False).items

        for object in resource_objects:
            result_dict[object.metadata.name] = object.to_dict()
        return result_dict

    def get_custom_resources(self, namespace: str, group: str, version: str,
                             plural: str) -> dict:
        # WIP

        # result_dict = {}
        custom_resources = self.customObjectApi.list_namespaced_custom_object(
            group, version, namespace, plural)
        # for cr in custom_resources:
        #     result_dict[cr.metadata.name] = cr.to_dict()
        return custom_resources

    def check_log(self, generation: int) -> RunResult:
        '''Check the operator log for error msg
        
        Returns
            RunResult of the checking
        '''
        operator_pod_list = self.corev1Api.list_namespaced_pod(
            namespace=self.namespace,
            watch=False,
            label_selector="acto/tag=operator-pod").items
        if len(operator_pod_list) >= 1:
            logging.debug('Got operator pod: pod name:' +
                          operator_pod_list[0].metadata.name)
        else:
            logging.error('Failed to find operator pod')

        log = self.corev1Api.read_namespaced_pod_log(
            name=operator_pod_list[0].metadata.name, namespace=self.namespace)

        with open('%s/operator-%d.log' % (self.cur_path, generation),
                  'w') as fout:
            fout.write(log)

        if log.find('error') != -1:
            logging.info('Found error in operator log')
            return RunResult.error

        return RunResult.passing