import subprocess
import time
import logging
from unicodedata import name
from deepdiff import DeepDiff
import json
import yaml
import re
from multiprocessing import Process, Queue
import queue
import copy
from kubernetes.client import *

from common import *
import acto_timer
from custom.compare import CompareMethods

class Result(object):
    def __init__(self, context: dict, prev_result = None, cli_result = None,\
        input_path = None, cli_output_path = None, delta_log_path = None,\
        system_state_path = None, operator_log_path = None, events_log_path = None):
        self.namespace: str     = context['namespace']
        self.crd_metainfo: dict = context['crd']
        self.prev_result        = prev_result
        self.cli_result         = cli_result
        self.log_num            = 0

        self.input_path         = input_path
        self.cli_output_path    = cli_output_path
        self.delta_log_path     = delta_log_path
        self.system_state_path  = system_state_path
        self.operator_log_path  = operator_log_path
        self.events_log_path    = events_log_path

        self.coreV1Api          = CoreV1Api()
        self.appV1Api           = AppsV1Api()
        self.batchV1Api         = BatchV1Api()
        self.customObjectApi    = CustomObjectsApi()
        self.policyV1Api        = PolicyV1Api()
        self.networkingV1Api    = NetworkingV1Api()
        self.resource_methods   = {
            'pod': self.coreV1Api.list_namespaced_pod,
            'stateful_set': self.appV1Api.list_namespaced_stateful_set,
            'deployment': self.appV1Api.list_namespaced_deployment,
            'config_map': self.coreV1Api.list_namespaced_config_map,
            'service': self.coreV1Api.list_namespaced_service,
            'pvc': self.coreV1Api.list_namespaced_persistent_volume_claim,
            'cronjob': self.batchV1Api.list_namespaced_cron_job,
            'ingress': self.networkingV1Api.list_namespaced_ingress,
            'pod_disruption_budget': self.policyV1Api.list_namespaced_pod_disruption_budget,
        }

    def setup_path_by_generation(self, cur_path: string, generation: int):
        '''An alternative way to setup path fields
        '''
        self.delta_log_path    = "%s/delta-%d.log"           % (cur_path, generation)
        self.operator_log_path = "%s/operator-%d.log"        % (cur_path, generation)
        self.system_state_path = "%s/system-state-%03d.json" % (cur_path, generation)
        self.events_log_path   = "%s/events.log"             % (cur_path)
        self.input_path        = "%s/mutated-%d.yaml"        % (cur_path, generation)
        self.cli_output_path   = "%s/cli-output-%d.log"      % (cur_path, generation)

    def get_deltas(self):
        curr_input, curr_system_state = {}, {}
        prev_input, prev_system_state = {}, {}

        # read input & system state from the current result
        with open(self.input_path, 'r') as f:
            curr_input = yaml.load(f, Loader=yaml.loader.SafeLoader)

        with open(self.system_state_path, 'r') as f:
            curr_system_state = json.load(f)
        
        # read input & system state from the previous result if possible
        if self.prev_result == None:
            prev_input = curr_input
            prev_system_state = {}
        else:
            with open(self.prev_result.input_path, 'r') as f:
                prev_input = yaml.load(f, Loader=yaml.loader.SafeLoader)
            with open(self.prev_result.system_state_path, 'r') as f:
                prev_system_state = json.load(f)

        input_delta = postprocess_diff(
                    DeepDiff(prev_input, 
                    curr_input,
                    ignore_order=True,
                    report_repetition=True,
                    view='tree'))
        
        system_state_delta = {}
        for resource in curr_system_state:
            if resource not in prev_system_state:
                prev_system_state[resource] = {}
            system_state_delta[resource] = postprocess_diff(
                        DeepDiff(prev_system_state[resource],
                        curr_system_state[resource],
                        exclude_regex_paths=EXCLUDE_PATH_REGEX,
                        report_repetition=True,
                        view='tree'))

        return input_delta, system_state_delta

    def get_cli_result(self) -> tuple[str, str]:
        cli_result = {}
        
        with open(self.cli_output_path, 'r') as f:
            cli_result = json.load(f)
        
        return cli_result['stdout'], cli_result['stderr']

    def get_operator_log(self):
        log = []
        
        with open(self.operator_log_path, 'r') as f:
             log = f.readlines()
             
        return log
        
    def collect_all_result(self):
        self.collect_events()
        self.collect_operator_log()
        self.collect_cli_output()
        self.collect_system_state()
        self.collect_delta() # delta must be collected after system state

    def collect_system_state(self):
        '''Queries resources in the test namespace, computes delta
        
        Args:
            result: includes the path to the resource state file
        '''
        resources = {}

        for resource, method in self.resource_methods.items():
            resources[resource] = self.__get_all_objects(method)
            
        current_cr = self.__get_custom_resources(self.namespace,
                                                 self.crd_metainfo['group'],
                                                 self.crd_metainfo['version'],
                                                 self.crd_metainfo['plural'])
        logging.debug(current_cr)

        resources['custom_resource_spec'] = current_cr['test-cluster']['spec'] \
            if 'spec' in current_cr['test-cluster'] else None
        resources['custom_resource_status'] = current_cr['test-cluster']['status'] \
            if 'status' in current_cr['test-cluster'] else None

        # Dump system state
        with open(self.system_state_path, 'w') as fout:
            json.dump(resources, fout, cls=ActoEncoder, indent=6)

    def collect_delta(self):
        input_delta, system_delta = self.get_deltas()
        with open(self.delta_log_path, 'w') as f:
            f.write('---------- INPUT DELTA  ----------\n')
            f.write(json.dumps(input_delta, cls=ActoEncoder, indent=6))
            f.write('\n---------- SYSTEM DELTA ----------\n')
            f.write(json.dumps(system_delta, cls=ActoEncoder, indent=6))

    def collect_operator_log(self):
        '''Queries operator log in the test namespace
        
        Args:
            result: includes the path to the operator log file
        '''
        operator_pod_list = self.coreV1Api.list_namespaced_pod(
            namespace=self.namespace,
            watch=False,
            label_selector="acto/tag=operator-pod").items

        if len(operator_pod_list) >= 1:
            logging.debug('Got operator pod: pod name:' +
                            operator_pod_list[0].metadata.name)
        else:
            logging.error('Failed to find operator pod')
            #TODO: refine what should be done if no operator pod can be found

        log = self.coreV1Api.read_namespaced_pod_log(
            name=operator_pod_list[0].metadata.name,
            namespace=self.namespace)

        # only get the new log since previous result
        new_log = log.split('\n')
        if self.prev_result != None:
            # exclude the old logs
            prev_log_num = self.prev_result.log_num
            new_log = new_log[prev_log_num:]

        self.log_num = len(new_log)

        with open(self.operator_log_path, 'a') as f:
            for line in new_log:
                f.write("%s\n" % line)

    def collect_events(self):
        events = self.coreV1Api.list_namespaced_event(self.namespace,
                                                pretty=True,
                                                _preload_content=True,
                                                watch=False)

        with open(self.events_log_path, 'w') as f:
            for event in events.items:
                f.write("%s %s %s %s:\t%s\n" % (
                    event.first_timestamp.strftime("%H:%M:%S") if event.first_timestamp != None else "None",
                    event.involved_object.kind,
                    event.involved_object.name,
                    event.involved_object.resource_version,
                    event.message))

    def collect_cli_output(self):
        cli_output = {}
        cli_output["stdout"] = self.cli_result.stdout
        cli_output["stderr"] = self.cli_result.stderr
        with open(self.cli_output_path, 'w') as f:
            f.write(json.dumps(cli_output, cls=ActoEncoder, indent=6))

    def __get_all_objects(self, method) -> dict:
        '''Get resources in the application namespace

        Args:
            method: function pointer for getting the object
        
        Returns
            resource in dict
        '''
        result_dict = {}
        resource_objects = method(namespace=self.namespace,
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

class Runner(object):
    def __init__(self, context: dict):
        self.namespace = context["namespace"]
        self.log_line = 0

        self.coreV1Api = CoreV1Api()
    
    def run(self, cmd: list) -> subprocess.CompletedProcess:
        '''Simply run the cmd and dumps system_state, delta, operator log, events and input files without checking. 
           The function blocks until system converges.

        Args:
            cmd: subprocess command to be executed using subprocess.run

        Returns:
            result 
        '''
        cli_result = subprocess.run(cmd, capture_output=True, text=True)
        self.wait_for_system_converge()

        logging.debug('STDOUT: ' + cli_result.stdout)
        logging.debug('STDERR: ' + cli_result.stderr)
        
        return cli_result

    def wait_for_system_converge(self, hard_timeout = 600):
        '''This function blocks until the system converges. It keeps 
           watching for incoming events. If there is no event within 
           60 seconds, the system is considered to have converged. 
        
        Args:
            hard_timeout: the maximal wait time for system convergence
        '''
        
        start_timestamp = time.time()
        logging.info("Waiting for system to converge... ")

        event_stream = self.coreV1Api.list_namespaced_event(self.namespace, 
                                                       _preload_content=False,
                                                       watch = True)

        combined_event_queue = Queue(maxsize = 0)
        timer_hard_timeout = acto_timer.ActoTimer(hard_timeout, combined_event_queue, "timeout")
        watch_process = Process(target=self.watch_system_events,
                        args=(event_stream, "event"))

        timer_hard_timeout.start()
        watch_process.start()

        while (True):
            try:
                event = combined_event_queue.get(timeout=60)
                if event == "timeout":
                    logging.debug('Hard timeout %d triggered', hard_timeout)
                    break
            except queue.Empty:
                break

        event_stream.close()
        timer_hard_timeout.cancel()
        watch_process.terminate()

        time_elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - start_timestamp))
        logging.info('System took %s to converge' % time_elapsed)

    def watch_system_events(self, event_stream, queue: Queue):
        '''A process that watches namespaced events
        '''
        for event in event_stream:
            try:
                queue.put(event)
            except:
                pass

class Checker(object):
    def __init__(self, context: dict) -> None:
        self.namespace      = context['namespace']
        self.compare_method = CompareMethods()

    def check(self, result: Result) -> RunResult:
        '''Use acto oracles against the results to check for any errors

        Args:        
            result: includes the path to result files

        Returns:
            RunResult of the checking
        '''
        input_result = self.check_input(result)
        state_result = self.check_resources(result)
        log_result = self.check_operator_log(result)

        if not isinstance(input_result, PassResult):
            return input_result
        if isinstance(log_result, InvalidInputResult):
            logging.info('Invalid input, skip this case')
            return log_result
        if isinstance(state_result, ErrorResult):
            logging.info('Report error from system state oracle')
            return state_result
        elif isinstance(log_result, ErrorResult):
            logging.info('Report error from operator log oracle')
            return log_result

        return PassResult()

    def check_input(self, result: Result) -> RunResult:
        stdout, stderr = result.get_cli_result()
        if stdout.find('error') != -1 or stderr.find(
                'error') != -1 or stderr.find('invalid') != -1:
            logging.info('Invalid input, reject mutation')
            logging.info('STDOUT: ' + stdout)
            logging.info('STDERR: ' + stderr)
            return InvalidInputResult()

        if stdout.find('unchanged') != -1 or stderr.find(
                'unchanged') != -1:
            logging.info('CR unchanged, continue')
            return UnchangedInputResult()

        return PassResult()

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
        input_delta, system_delta = result.get_deltas()
        
        # cr_spec_diff is same as input delta, so it is excluded
        system_delta_without_cr = copy.deepcopy(system_delta)
        system_delta_without_cr.pop('custom_resource_spec')
        
        for delta_list in input_delta.values():
            for delta in delta_list.values():
                if self.compare_method.input_compare(delta.prev, delta.curr):
                    # if the input delta is considered as equivalent, skip
                    continue

                # Find the longest matching field, compare the delta change
                match_deltas = self._list_matched_fields(delta.path,
                                                   system_delta_without_cr)

                # TODO: should the delta match be inclusive?
                for match_delta in match_deltas:
                    logging.debug('Input delta [%s] matched with [%s]' %
                                  (delta.path, match_delta.path))
                    if not self.compare_method.compare(delta.prev, delta.curr,
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
                                if self.compare_method.compare(
                                    delta.prev, delta.curr, state_delta.prev,
                                    state_delta.curr):
                                    found = True
                    if found:
                        continue
                    logging.error('Found no matching fields for input delta')
                    logging.error('Input delta [%s]' % delta.path)
                    return ErrorResult(Oracle.SYSTEM_STATE,
                                       'Found no matching fields for input',
                                       delta)
        return PassResult()
    
    def check_operator_log(self, result: Result) -> RunResult:
        '''Check the operator log for error msg
        
        Args:
            result - includes the path to delta log files

        Returns:
            RunResult of the checking
        '''
        log = result.get_operator_log()

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

    def check_events_log(self, result: Result) -> RunResult:
        pass

    def _list_matched_fields(self, path: list, delta_dict: dict) -> list:
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

# check file testing
if __name__ == "__main__":
    import subprocess
    import kubernetes

    testrun_folder = "../testrun-2022-06-02-14-13/"
    not_present_trial = testrun_folder + "trial-0013"
    context = {"namespace": "default", \
        "crd": {"group": "redis.redis.opstreelabs.in", "plural": "redisclusters", "version": "v1beta1"}}
    cmd = ["ls", "trial-0005"]

    # Populate the Result, Runner and Checker classes
    runner = Runner(context)
    checker = Checker(context)
    result_0 = Result(context, None, subprocess.run(cmd, capture_output=True, text=True))
    result_0.setup_path_by_generation(not_present_trial, 0)
    
    print("cli functionality test")
    result_0.collect_cli_output()
    assert(result_0.get_cli_result()[0] == subprocess.run(cmd, capture_output=True, text=True).stdout)
    assert(result_0.get_cli_result()[1] == subprocess.run(cmd, capture_output=True, text=True).stderr)
    # test operator log retrieval
    print(result_0.get_operator_log())
    print("cli functionality test passed\n")

    # test delta retrieval for result without previous result
    print("delta retrieval test")
    input_delta, sys_delta = result_0.get_deltas()
    assert(input_delta == {})

    result_0.collect_delta()
    delta_generated = ""
    delta_original = ""
    with open("%s/delta-%d.log" % (not_present_trial, 0), 'r') as f:
        delta_generated = f.readlines()
    with open("%s/delta-%d-original.log" % (not_present_trial, 0), 'r') as f:
        delta_original = f.readlines()
    print(DeepDiff(delta_generated, delta_original))
    print("delta retrieval test passed\n")
    
    print("checker test")
    # result without previous result should always pass check 
    assert(isinstance(checker.check_resources(result_0), PassResult))
    assert(isinstance(checker.check_operator_log(result_0), PassResult))
    assert(isinstance(checker.check_input(result_0), PassResult))
    assert(isinstance(checker.check(result_0), PassResult))

    result_1 = Result(context, result_0, subprocess.run(cmd, capture_output=True, text=True))
    result_1.setup_path_by_generation(not_present_trial, 1)
    result_1.collect_cli_output()

    # result for the last trial should pass as well
    assert(isinstance(checker.check_resources(result_1), PassResult))
    assert(isinstance(checker.check_operator_log(result_1), PassResult))
    assert(isinstance(checker.check_input(result_1), PassResult))
    assert(isinstance(checker.check(result_1), PassResult))

    print("checker test passed, not present works")

    # print(result_1.get_deltas())
    result_1.collect_delta()

    print("Mimicking Acto run")
    
    subprocess.run(["kind", "delete", "cluster"])
    subprocess.run(["kind", "create", "cluster", "--image", "kindest/node:v1.22.9"])
    time.sleep(5)
    subprocess.run(["kubectl", "apply", "-f", "data/redis-ot-container-kit-operator/bundle_f1c547e.yaml"])
    kubernetes.config.load_kube_config()
    # time.sleep(25)

    result_run = Result(context, result_0, runner.run(["kubectl", "apply", "-f", "mutated-1.yaml"]))
    result_run.setup_path_by_generation(not_present_trial, 1)
    result_run.collect_cli_output()
    result_run.collect_events()
    result_run.collect_system_state()
    result_run.collect_delta()
    # result_run.collect_all_result()
    assert(isinstance(checker.check(result_run), PassResult))
    print("Mimicking Acto run Passed")



