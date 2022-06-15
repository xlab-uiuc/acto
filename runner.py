import kubernetes
import subprocess
import logging
from multiprocessing import Process, Queue
import time
import queue
import json
import yaml

import acto_timer
from snapshot import Snapshot
from common import *


class Runner(object):

    def __init__(self, context: dict, trial_dir: str, cluster_name: str):
        self.namespace = context["namespace"]
        self.crd_metainfo: dict = context['crd']
        self.trial_dir = trial_dir
        self.cluster_name = cluster_name

        apiclient = kubernetes_client(cluster_name)
        self.coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        self.appV1Api = kubernetes.client.AppsV1Api(apiclient)
        self.batchV1Api = kubernetes.client.BatchV1Api(apiclient)
        self.customObjectApi = kubernetes.client.CustomObjectsApi(apiclient)
        self.policyV1Api = kubernetes.client.PolicyV1Api(apiclient)
        self.networkingV1Api = kubernetes.client.NetworkingV1Api(apiclient)
        self.resource_methods = {
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

    def run(self, input: dict, generation: int) -> Snapshot:
        '''Simply run the cmd and dumps system_state, delta, operator log, events and input files without checking. 
           The function blocks until system converges.

        Args:
            cmd: subprocess command to be executed using subprocess.run

        Returns:
            result 
        '''
        self.operator_log_path = "%s/operator-%d.log" % (self.trial_dir, generation)
        self.system_state_path = "%s/system-state-%03d.json" % (self.trial_dir, generation)
        self.events_log_path = "%s/events.log" % (self.trial_dir)
        self.cli_output_path = "%s/cli-output-%d.log" % (self.trial_dir, generation)

        mutated_filename = '%s/mutated-%d.yaml' % (self.trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump(input, mutated_cr_file)

        cmd = ['apply', '-f', mutated_filename, '-n', self.namespace]

        cli_result = kubectl(cmd, cluster_name=self.cluster_name, capture_output=True, text=True)
        self.wait_for_system_converge()

        logging.debug('STDOUT: ' + cli_result.stdout)
        logging.debug('STDERR: ' + cli_result.stderr)

        # if connection refused occurs, we cannot collect the system state since it is empty
        try:
            system_state = self.collect_system_state()
            operator_log = self.collect_operator_log()
            events_log = self.collect_events()
        except KeyError as e:
            logging.warn(e)
            system_state = {}
            operator_log = None

        snapshot = Snapshot(input, self.collect_cli_result(cli_result), system_state, operator_log)
        return snapshot

    def run_without_collect(self, seed_file: str):
        cmd = ['apply', '-f', seed_file, '-n', self.context['namespace']]
        _ = kubectl(cmd, cluster_name=self.cluster_name)

        self.wait_for_system_converge()

    def collect_system_state(self) -> dict:
        '''Queries resources in the test namespace, computes delta
        
        Args:
            result: includes the path to the resource state file
        '''
        resources = {}

        for resource, method in self.resource_methods.items():
            resources[resource] = self.__get_all_objects(method)

        current_cr = self.__get_custom_resources(self.namespace, self.crd_metainfo['group'],
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

        return resources

    def collect_operator_log(self) -> list:
        '''Queries operator log in the test namespace
        
        Args:
            result: includes the path to the operator log file
        '''
        operator_pod_list = self.coreV1Api.list_namespaced_pod(
            namespace=self.namespace, watch=False, label_selector="acto/tag=operator-pod").items

        if len(operator_pod_list) >= 1:
            logging.debug('Got operator pod: pod name:' + operator_pod_list[0].metadata.name)
        else:
            logging.error('Failed to find operator pod')
            #TODO: refine what should be done if no operator pod can be found

        log = self.coreV1Api.read_namespaced_pod_log(name=operator_pod_list[0].metadata.name,
                                                     namespace=self.namespace)

        # only get the new log since previous result
        new_log = log.split('\n')

        with open(self.operator_log_path, 'a') as f:
            for line in new_log:
                f.write("%s\n" % line)

        return new_log

    def collect_events(self):
        events = self.coreV1Api.list_namespaced_event(self.namespace,
                                                      pretty=True,
                                                      _preload_content=True,
                                                      watch=False)

        with open(self.events_log_path, 'w') as f:
            for event in events.items:
                f.write("%s %s %s %s:\t%s\n" %
                        (event.first_timestamp.strftime("%H:%M:%S") if event.first_timestamp != None
                         else "None", event.involved_object.kind, event.involved_object.name,
                         event.involved_object.resource_version, event.message))

    def collect_cli_result(self, p: subprocess.CompletedProcess):
        cli_output = {}
        cli_output["stdout"] = p.stdout
        cli_output["stderr"] = p.stderr
        with open(self.cli_output_path, 'w') as f:
            f.write(json.dumps(cli_output, cls=ActoEncoder, indent=6))
        return p.stdout, p.stderr

    def __get_all_objects(self, method) -> dict:
        '''Get resources in the application namespace

        Args:
            method: function pointer for getting the object
        
        Returns
            resource in dict
        '''
        result_dict = {}
        resource_objects = method(namespace=self.namespace, watch=False).items

        for object in resource_objects:
            result_dict[object.metadata.name] = object.to_dict()
        return result_dict

    def __get_custom_resources(self, namespace: str, group: str, version: str, plural: str) -> dict:
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

    def wait_for_system_converge(self, hard_timeout=600):
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
                                                            watch=True)

        combined_event_queue = Queue(maxsize=0)
        timer_hard_timeout = acto_timer.ActoTimer(hard_timeout, combined_event_queue, "timeout")
        watch_process = Process(target=self.watch_system_events,
                                args=(event_stream, combined_event_queue))

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