import subprocess
import time
import logging
from deepdiff import DeepDiff
import json
import re
from threading import Thread
import copy
import kubernetes

from common import RunResult, ActoEncoder, postprocess_diff, EXCLUDE_PATH_REGEX, EXCLUDE_ERROR_REGEX, canonicalize
import acto_timer


class Checker:

    def __init__(self, context: dict, cur_path: str) -> None:
        self.context = context
        self.cur_path = cur_path
        self.corev1Api = kubernetes.client.CoreV1Api()
        self.appv1Api = kubernetes.client.AppsV1Api()
        self.customObjectApi = kubernetes.client.CustomObjectsApi()
        self.resources = {}

        self.resource_methods = {
            'pod': self.corev1Api.list_namespaced_pod,
            'stateful_set': self.appv1Api.list_namespaced_stateful_set,
            'config_map': self.corev1Api.list_namespaced_config_map,
            'service': self.corev1Api.list_namespaced_service,
        }

        for resource in self.resource_methods:
            self.resources[resource] = {}
        self.resources['custom_resource'] = {}

    def check_resources(self, input_diff, generation: int):
        '''Queries resources in the test namespace, computes delta
        
        Args:
            input_diff: delta in the CR yaml input
            generation: at which step in the trial
        '''
        input_delta = postprocess_diff(input_diff)
        system_delta = {}
        for resource, method in self.resource_methods.items():
            current_resource = self.__get_all_objects(method)
            system_delta[resource] = postprocess_diff(
                DeepDiff(self.resources[resource],
                         current_resource,
                         exclude_regex_paths=EXCLUDE_PATH_REGEX,
                         report_repetition=True,
                         view='tree'))
            self.resources[resource] = current_resource

        current_cr = self.__get_custom_resources(self.context['namespace'],
                                                 self.context['crd']['group'],
                                                 self.context['crd']['version'],
                                                 self.context['crd']['plural'])
        logging.debug(current_cr)

        system_delta['cr_diff'] = postprocess_diff(
            DeepDiff(self.resources['custom_resource'],
                     current_cr,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.resources['custom_resource'] = current_cr

        with open('%s/delta-%d.log' % (self.cur_path, generation), 'w') as fout:
            fout.write('---------- INPUT DELTA  ----------\n')
            fout.write(json.dumps(input_delta, cls=ActoEncoder, indent=6))
            fout.write('\n---------- SYSTEM DELTA ----------\n')
            fout.write(json.dumps(system_delta, cls=ActoEncoder, indent=6))
        '''
        System state oracle

        For each delta in the input, find the longest matching fields in the system state.
        Then compare the the delta values (prev, curr).
        '''
        system_delta_without_cr = copy.deepcopy(system_delta)
        system_delta_without_cr.pop('cr_diff')
        for delta_list in input_delta.values():
            for delta in delta_list.values():
                # Find the longest matching field, compare the delta change
                match_deltas = list_matched_fields(delta.path,
                                                   system_delta_without_cr)
                for match_delta in match_deltas:
                    logging.debug('Input delta [%s] matched with [%s]' %
                                  (delta.path, match_delta.path))
                    if delta.prev != match_delta.prev or delta.curr != match_delta.curr:
                        logging.error(
                            'Matched delta inconsistent with input delta')
                        logging.error('Input delta: %s -> %s' %
                                      (delta.prev, delta.curr))
                        logging.error('Matched delta: %s -> %s' %
                                      (match_delta.prev, match_delta.curr))
                        return RunResult.error

                if len(match_deltas) == 0:
                    # if prev and curr of the delta are the same, also consider it as a match
                    found = False
                    for resource_delta_list in system_delta_without_cr.values():
                        for type_delta_list in resource_delta_list.values():
                            for state_delta in type_delta_list.values():
                                if delta.prev == state_delta.prev \
                                    and delta.curr == state_delta.curr:
                                    found = True
                    if found:
                        break
                    logging.error('Found no matching fields for input delta')
                    logging.error('Input delta [%s]' % delta.path)
                    return RunResult.error

        return RunResult.passing

    def check_health(self) -> RunResult:
        '''System health oracle'''
        # TODO: Add other resources, e.g. deployment
        for sts in self.resources['stateful_set'].values():
            desired_replicas = sts['status']['replicas']
            if 'ready_replicas' not in sts['status']:
                logging.error('StatefulSet unhealthy ready replicas None')
                return RunResult.error
            available_replicas = sts['status']['ready_replicas']
            if desired_replicas != available_replicas:
                logging.error(
                    'StatefulSet unhealthy desired replicas [%s] available replicas [%s]'
                    % (desired_replicas, available_replicas))
                return RunResult.error
        return RunResult.passing

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
                'error') != -1 or cli_result.stderr.find('invalid') != -1:
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

        result = self.check_resources(input_diff, generation)
        if result != RunResult.passing:
            logging.info('Report error from system state oracle')
            return result

        # result = self.check_health()
        # if result != RunResult.passing:
        #     logging.info('Report error from system health oracle')
        #     return result

        result = self.check_log(generation)
        if result != RunResult.passing:
            logging.info('Report error from operator log oracle')
            return result

        return RunResult.passing

    def __get_all_objects(self, method) -> dict:
        '''Get all pods in the application namespace

        Args:
            method: function pointer for getting the object
        
        Returns
            dict of all pods
        '''
        result_dict = {}
        resource_objects = method(namespace=self.context['namespace'],
                                  watch=False).items

        for object in resource_objects:
            result_dict[object.metadata.name] = object.to_dict()
        return result_dict

    def __get_custom_resources(self, namespace: str, group: str, version: str,
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
        return result_dict

    def check_log(self, generation: int) -> RunResult:
        '''Check the operator log for error msg
        
        Returns
            RunResult of the checking
        '''
        operator_pod_list = self.corev1Api.list_namespaced_pod(
            namespace=self.context['namespace'],
            watch=False,
            label_selector="acto/tag=operator-pod").items
        if len(operator_pod_list) >= 1:
            logging.debug('Got operator pod: pod name:' +
                          operator_pod_list[0].metadata.name)
        else:
            logging.error('Failed to find operator pod')

        log = self.corev1Api.read_namespaced_pod_log(
            name=operator_pod_list[0].metadata.name,
            namespace=self.context['namespace'])

        with open('%s/operator-%d.log' % (self.cur_path, generation),
                  'w') as fout:
            fout.write(log)

        for line in log.split('\n'):
            if 'error' in line:
                skip = False
                for regex in EXCLUDE_ERROR_REGEX:
                    if re.search(regex, line):
                        logging.debug('Skipped error msg: %s' % line)
                        skip = True
                if skip:
                    continue
                logging.info('Found error in operator log')
                return RunResult.error
            else:
                continue

        return RunResult.passing

    def wait_for_system_converge(self, timeout=360):
        '''This function blocks until the system converges

        It sets up a resettable timer which goes off in 60 seconds.
        It starts a thread that watches for system events, every time a system
        event arrives, this thread resets the timer.
        '''
        start = time.time()
        timer = acto_timer.ActoTimer(60)
        watch_thread = Thread(
            target=watch_system_events,
            args=[self.corev1Api, self.context['namespace'], timer])
        timer.start()
        watch_thread.start()

        timer.join(timeout)
        timer.cancel()
        time_elapsed = time.strftime("%H:%M:%S",
                                     time.gmtime(time.time() - start))
        logging.info('System took %s to converge' % time_elapsed)
        return


def watch_system_events(api, namespace, timer: acto_timer.ActoTimer):
    '''A function thread that watches namespaced events
    '''
    # TODO: get rid of watch
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


def list_matched_fields(path: list, delta_dict: dict) -> list:
    '''Search through the entire system delta to find longest matching field
    
    Args:
        path: path of input delta as list
        delta_dict: dict of system delta

    Returns:
        list of system delta with longest matching field path with input delta
    '''
    results = []
    max_match = 0
    for resource_delta_list in delta_dict.values():
        for type_delta_list in resource_delta_list.values():
            for delta in type_delta_list.values():
                position = 0
                print(type(path[0]))
                while canonicalize(path[-position - 1]) == canonicalize(
                        delta.path[-position - 1]):
                    position += 1
                    if position == min(len(path), len(delta.path)):
                        break
                if position == max_match and position != 0:
                    results.append(delta)
                elif position > max_match:
                    results = [delta]
                    max_match = position
                else:
                    pass

    return results