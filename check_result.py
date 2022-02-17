import subprocess
import time
import logging
from deepdiff import DeepDiff
import json
import re
from threading import Thread, Event

from common import RunResult, ActoEncoder, postprocess_diff, EXCLUDE_PATH_REGEX, EXCLUDE_ERROR_REGEX
import acto_timer


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

        resource_diff = {'input_diff': postprocess_diff(input_diff)}
        # Check pods
        current_pods = self.get_all_objects(self.corev1Api.list_namespaced_pod)
        resource_diff['pods_diff'] = postprocess_diff(
            DeepDiff(self.pods,
                     current_pods,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.pods = current_pods
        logging.debug(current_pods)

        # Check statefulSets
        current_sts = self.get_all_objects(
            self.appv1Api.list_namespaced_stateful_set)
        resource_diff['sts_diff'] = postprocess_diff(
            DeepDiff(self.stateful_sets,
                     current_sts,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.stateful_sets = current_sts

        current_config_maps = self.get_all_objects(
            self.corev1Api.list_namespaced_config_map)
        resource_diff['configmap_diff'] = postprocess_diff(
            DeepDiff(self.config_maps,
                     current_config_maps,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.config_maps = current_config_maps

        current_services = self.get_all_objects(
            self.corev1Api.list_namespaced_service)
        resource_diff['services_diff'] = postprocess_diff(
            DeepDiff(self.services,
                     current_services,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.services = current_services

        current_cr = self.get_custom_resources(self.namespace, 'rabbitmq.com',
                                               'v1beta1', 'rabbitmqclusters')
        logging.debug(current_cr)

        resource_diff['cr_diff'] = postprocess_diff(
            DeepDiff(self.customResource,
                     current_cr,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.customResource = current_cr

        with open('%s/delta-%d.log' % (self.cur_path, generation), 'w') as fout:
            json.dump(resource_diff, fout, cls=ActoEncoder, indent=6)

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

        self.wait_for_system_converge()

        self.check_resources(input_diff, generation)

        return self.check_log(generation)

    def get_all_objects(self, method) -> dict:
        '''Get all pods in the application namespace

        Args:
            method: function pointer for getting the object
        
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
        '''Get custom resource object

        Args:
            namespace: namespace of the cr
            group: API group of the cr
            version: version of the cr
            plural: plural name of the cr
        
        Returns
        '''
        result_dict = {}
        custom_resources = self.customObjectApi.list_namespaced_custom_object(
            group, version, namespace, plural)['items']
        for cr in custom_resources:
            result_dict[cr['metadata']['name']] = cr
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

        for line in log.split('\n'):
            if 'error' in line:
                skip = False
                for regex in EXCLUDE_ERROR_REGEX:
                    if re.search(regex, line):
                        skip = True
                if skip:
                    continue
                logging.info('Found error in operator log')
                return RunResult.error
            else:
                continue

        return RunResult.passing

    def wait_for_system_converge(self, timeout=60):
        '''This function blocks until the system converges
        '''
        start = time.time()
        timer = acto_timer.ActoTimer(timeout)
        watch_thread = Thread(target=watch_system_events,
                              args=[self.corev1Api, self.namespace, timer])
        timer.start()
        watch_thread.start()

        timer.join()
        time_elapsed = time.strftime("%H:%M:%S",
                                     time.gmtime(time.time() - start))
        logging.info('System took %s to converge' % time_elapsed)
        return


def watch_system_events(api, namespace, timer: acto_timer.ActoTimer):
    ret = api.list_namespaced_event(namespace,
                                    _preload_content=False,
                                    watch=True)
    for _ in ret:
        if timer.is_alive():
            timer.reset()
        else:
            break
    ret.close()
    ret.release_conn()