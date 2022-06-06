import subprocess
import time
import logging
from unicodedata import name
from deepdiff import DeepDiff
import json
import re
from multiprocessing import Process, Queue
import queue
import copy
import kubernetes
from custom.compare import CompareMethods

from common import *
import acto_timer

class Result(object):
    def __init__(self, cli_result = None, input_diff = None, delta_log_path = None, \
        operator_log_path = None, system_state_path = None, events_log_path = None):
        self.cli_result        = cli_result            # subprocess.CompletedProcess
        self.input_diff        = input_diff
        self.delta_log_path    = delta_log_path
        self.operator_log_path = operator_log_path
        self.system_state_path = system_state_path
        self.events_log_path   = events_log_path

    def setup_path_by_generation(self, cur_path: string, generation: int):
        '''An alternative way to setup path fields
        '''
        self.delta_log_path    = "%s/delta-%d.log"    % (cur_path, generation)
        self.operator_log_path = "%s/operator-%d.log" % (cur_path, generation)
        self.system_state_path = "%s/system-state-%03d.json" % (cur_path, generation)
        self.events_log_path   = "%s/events.log"      % (cur_path)

    def get_cli_result(self):
        return self.cli_result

    def get_input_diff(self):
        return self.input_diff

    def get_delta_log_path(self):
        return self.delta_log_path
    
    def get_operator_log_path(self):
        return self.operator_log_path
    
    def get_system_state_path(self):
        return self.system_state_path

    def get_events_log_path(self):
        return self.events_log_path

class Checker:

    def __init__(self, context: dict) -> None:
        self.context = context
        self.cur_path = context['current_dir_path']
        self.corev1Api = kubernetes.client.CoreV1Api()
        self.appv1Api = kubernetes.client.AppsV1Api()
        self.batchv1Api = kubernetes.client.BatchV1Api()
        self.customObjectApi = kubernetes.client.CustomObjectsApi()
        self.resources = {}
        self.log_line = 0

        self.compare = CompareMethods()

        self.resource_methods = {
            'pod': self.corev1Api.list_namespaced_pod,
            'stateful_set': self.appv1Api.list_namespaced_stateful_set,
            'deployment': self.appv1Api.list_namespaced_deployment,
            'config_map': self.corev1Api.list_namespaced_config_map,
            'service': self.corev1Api.list_namespaced_service,
            'pvc': self.corev1Api.list_namespaced_persistent_volume_claim,
            'cronjob': self.batchv1Api.list_namespaced_cron_job,
            'ingress': kubernetes.client.NetworkingV1Api().list_namespaced_ingress,
        }

        for resource in self.resource_methods:
            self.resources[resource] = {}
        self.resources['custom_resource_status'] = {}
        self.resources['custom_resource_spec'] = {}

    def dump_all(self, result: Result):
        self.dump_events(result)
        self.dump_resource_states(result)
        self.dump_operator_log(result)

    def dump_events(self, result: Result):
        events = self.corev1Api.list_namespaced_event(self.context['namespace'],
                                                pretty=True,
                                                _preload_content=True,
                                                watch=False)

        with open(result.get_events_log_path(), 'w') as fout:
            for event in events.items:
                fout.write("%s %s %s %s:\t%s\n" % (
                    event.first_timestamp.strftime("%H:%M:%S") if event.first_timestamp != None else "None",
                    event.involved_object.kind,
                    event.involved_object.name,
                    event.involved_object.resource_version,
                    event.message))

    def dump_resource_states(self, result: Result):
        '''Queries resources in the test namespace, computes delta
        
        Args:
            result: includes the path to the resource state file
        '''

        input_delta = postprocess_diff(result.get_input_diff())
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

        current_cr_spec = current_cr['test-cluster']['spec'] if 'spec' in current_cr['test-cluster'] else None
        current_cr_status = current_cr['test-cluster']['status'] if 'status' in current_cr['test-cluster'] else None

        system_delta['cr_status_diff'] = postprocess_diff(
            DeepDiff(self.resources['custom_resource_status'],
                     current_cr_status,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.resources['custom_resource_status'] = current_cr_status

        system_delta['cr_spec_diff'] = postprocess_diff(
            DeepDiff(self.resources['custom_resource_spec'],
                     current_cr_spec,
                     exclude_regex_paths=EXCLUDE_PATH_REGEX,
                     report_repetition=True,
                     view='tree'))
        self.resources['custom_resource_spec'] = current_cr_spec

        # Dump system delta
        with open(result.get_delta_log_path(), 'w') as fout:
            fout.write('---------- INPUT DELTA  ----------\n')
            fout.write(json.dumps(input_delta, cls=ActoEncoder, indent=6))
            fout.write('\n---------- SYSTEM DELTA ----------\n')
            fout.write(json.dumps(system_delta, cls=ActoEncoder, indent=6))

        # Dump system state
        with open(result.get_system_state_path(), 'w') as fout:
            json.dump(self.resources, fout, cls=ActoEncoder, indent=6)

    def dump_operator_log(self, result: Result):
        '''Queries operator log in the test namespace
        
        Args:
            result: includes the path to the operator log file
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

        # only get the new log since last time
        log_lines = log.split('\n')
        new_log_lines = log_lines[self.log_line:]
        self.log_line = len(log_lines)

        with open(result.get_operator_log_path(), 'a') as fout:
            for line in new_log_lines:
                fout.write("%s\n" % line)


    def parse_delta(self, result: Result):
        '''Parse input and system state delta from delta logs
        
        Args:
            result: includes the path to the delta log file
        '''
        curr_section = ""
        input_diff_str = ""
        system_diff_str = ""
        with open(result.get_delta_log_path(), 'r') as f:
            for line in f.readlines():
                if line == "---------- INPUT DELTA  ----------\n":
                    curr_section = 'input'
                elif line == '---------- SYSTEM DELTA ----------\n':
                    curr_section = 'system'
                elif curr_section == 'input':
                    input_diff_str += line
                elif curr_section == 'system':
                    system_diff_str += line
        return (json.loads(input_diff_str), json.loads(system_diff_str))

    def check_resources(self, result: Result) -> RunResult:
        '''
        System state oracle

        For each delta in the input, find the longest matching fields in the system state.
        Then compare the the delta values (prev, curr).

        Args:
            result - includes the path to delta log files

        Returns:
            RunResult of the checking
        '''
        input_delta, system_delta = self.parse_delta(result)
        # TODO: Include the cr.status diff
        system_delta_without_cr = copy.deepcopy(system_delta)
        system_delta_without_cr.pop('cr_spec_diff')
        for delta_list in input_delta.values():
            for delta in delta_list.values():
                delta = Diff(delta['prev'], delta['curr'], delta['path'])
                if self.compare.input_compare(delta.prev, delta.curr):
                    # if the input delta is considered as equivalent, skip
                    continue

                # Find the longest matching field, compare the delta change
                match_deltas = list_matched_fields(delta.path,
                                                   system_delta_without_cr)
                for match_delta in match_deltas:
                    logging.debug('Input delta [%s] matched with [%s]' %
                                  (delta.path, match_delta.path))
                    if not self.compare.compare(delta.prev, delta.curr,
                                                match_delta.prev,
                                                match_delta.curr):
                        logging.error(
                            'Matched delta inconsistent with input delta')
                        logging.error('Input delta: %s -> %s' %
                                      (delta.prev, delta.curr))
                        logging.error('Matched delta: %s -> %s' %
                                      (match_delta.prev, match_delta.curr))
                        return ErrorResult(
                            Oracle.SYSTEM_STATE,
                            'Matched delta inconsistent with input delta',
                            delta, match_delta)

                if len(match_deltas) == 0:
                    # if prev and curr of the delta are the same, also consider it as a match
                    found = False
                    for resource_delta_list in system_delta_without_cr.values():
                        for type_delta_list in resource_delta_list.values():
                            for state_delta in type_delta_list.values():
                                state_delta = Diff(state_delta['prev'], state_delta['curr'], state_delta['path'])
                                if self.compare.compare(
                                    delta.prev, delta.curr, state_delta.prev,
                                    state_delta.curr):
                                    found = True
                    if found:
                        break
                    logging.error('Found no matching fields for input delta')
                    logging.error('Input delta [%s]' % delta.path)
                    return ErrorResult(Oracle.SYSTEM_STATE,
                                       'Found no matching fields for input',
                                       delta)

        return PassResult()

    def check_operator_log(self, result: Result)-> RunResult:
        '''Check the operator log for error msg
        
        Args:
            result - includes the path to delta log files

        Returns:
            RunResult of the checking
        '''
        # parse operator
        log = []
        with open(result.get_operator_log_path(), 'r') as f:
            log = f.readlines()

        for line in log:
            if invalid_input_message(line):
                return InvalidInputResult()
            elif 'error' in line.lower():
                skip = False
                for regex in EXCLUDE_ERROR_REGEX:
                    if re.search(regex, line):
                        logging.debug('Skipped error msg: %s' % line)
                        skip = True
                if skip:
                    continue
                logging.error('Found error in operator log')
                return ErrorResult(Oracle.ERROR_LOG, line)
            else:
                continue

        return PassResult()

    def check_health(self) -> RunResult:
        '''System health oracle'''
        # TODO: Add other resources, e.g. deployment
        for sts in self.resources['stateful_set'].values():
            desired_replicas = sts['status']['replicas']
            if 'ready_replicas' not in sts['status']:
                logging.error('StatefulSet unhealthy ready replicas None')
                return None  # TODO
            available_replicas = sts['status']['ready_replicas']
            if desired_replicas != available_replicas:
                logging.error(
                    'StatefulSet unhealthy desired replicas [%s] available replicas [%s]'
                    % (desired_replicas, available_replicas))
                return None  # TODO
        return PassResult()

    def __get_all_objects(self, method) -> dict:
        '''Get resources in the application namespace

        Args:
            method: function pointer for getting the object
        
        Returns
            resource in dict
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
        
        Returns:
            custom resouce object
        '''
        result_dict = {}
        custom_resources = self.customObjectApi.list_namespaced_custom_object(
            group, version, namespace, plural)['items']
        for cr in custom_resources:
            result_dict[cr['metadata']['name']] = cr
        return result_dict
    
    def run(self, cmd: list) -> subprocess.CompletedProcess:
        '''Simply run the cmd without checking, the function blocks until system converges

        Args:
            cmd: subprocess command to be executed using subprocess.run

        Returns:
            result returned by subprocess.run
        '''
        cli_result = subprocess.run(cmd, capture_output=True, text=True)
        logging.debug('STDOUT: ' + cli_result.stdout)
        logging.debug('STDERR: ' + cli_result.stderr)
        self.wait_for_system_converge()

        return cli_result

    def check(self, result: Result) -> RunResult:
        '''Use acto oracles against the results to check for any errors

        Args:        
            result: includes the path to result files

        Returns:
            RunResult of the checking
        '''


        cli_result = result.get_cli_result()
        if cli_result.stdout.find('error') != -1 or cli_result.stderr.find(
                'error') != -1 or cli_result.stderr.find('invalid') != -1:
            logging.error('Invalid input, reject mutation')
            logging.error('STDOUT: ' + cli_result.stdout)
            logging.error('STDERR: ' + cli_result.stderr)
            return InvalidInputResult()

        if cli_result.stdout.find('unchanged') != -1 or cli_result.stderr.find(
                'unchanged') != -1:
            logging.error('CR unchanged, continue')
            return UnchangedInputResult()

        state_result = self.check_resources(result)
        log_result = self.check_operator_log(result)

        if isinstance(log_result, InvalidInputResult):
            logging.debug('Invalid input, skip this case')
            return log_result

        if isinstance(state_result, ErrorResult):
            logging.info('Report error from system state oracle')
            return state_result
        elif isinstance(log_result, ErrorResult):
            logging.info('Report error from operator log oracle')
            return log_result

        return PassResult()


    def wait_for_system_converge(self, timeout=600):
        '''This function blocks until the system converges
        It sets up a resettable timer which goes off in 60 seconds.
        It starts a thread that watches for system events. 
        When a event occurs, the function is notified and it will reset the timer thread.
        '''
        logging.info('Waiting for system to converge...')
        ret = self.corev1Api.list_namespaced_event(self.context['namespace'],
                                                   _preload_content=False,
                                                   watch=True)

        combined_queue = Queue(maxsize=0)

        timer_timeout = acto_timer.ActoTimer(timeout, combined_queue, "timeout")
        watch_thread = Process(target=watch_system_events,
                               args=(ret, combined_queue, "event"))

        start = time.time()

        timer_timeout.start()
        watch_thread.start()
        while (True):
            try:
                msg = combined_queue.get(timeout=60)
            except queue.Empty:
                break
            if msg == "timeout":
                logging.debug('Hard timeout triggered')
                break

        combined_queue.close()

        timer_timeout.cancel()
        watch_thread.terminate()

        ret.close()
        ret.release_conn()

        time_elapsed = time.strftime("%H:%M:%S",
                                     time.gmtime(time.time() - start))

        logging.info('System took %s to converge' % time_elapsed)
        return


def watch_system_events(ret, queue: Queue, queue_msg):
    '''A function thread that watches namespaced events
    '''
    for _ in ret:
        # the queue might have been closed. It is safe to do so because system has converged
        try:
            queue.put(queue_msg)
        except:
            pass


def list_matched_fields(path: list, delta_dict: dict) -> list:
    '''Search through the entire system delta to find longest matching field
    
    Args:
        path: path of input delta as list
        delta_dict: dict of system delta

    Returns:
        list of system delta with longest matching field path with input delta
    '''
    # if the name of the field is generic, don't match using the path
    for regex in GENERIC_FIELDS:
        if re.search(regex, str(path[-1])):
            return []

    results = []
    max_match = 0
    for resource_delta_list in delta_dict.values():
        for type_delta_list in resource_delta_list.values():
            for delta in type_delta_list.values():
                delta = Diff(delta['prev'], delta['curr'], delta['path'])
                position = 0
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
