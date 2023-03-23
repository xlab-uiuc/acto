import kubernetes
import subprocess
from multiprocessing import Process, Queue
import time
import queue
import json
import yaml
import base64

import acto_timer
from client.kubectl import KubectlClient
from snapshot import Snapshot
from common import *
from thread_logger import get_thread_logger


class Runner(object):

    def __init__(self, context: dict, trial_dir: str, kubeconfig: str, context_name: str, wait_time: int = 45):
        self.namespace = context["namespace"]
        self.crd_metainfo: dict = context['crd']
        self.trial_dir = trial_dir
        self.kubeconfig = kubeconfig
        self.context_name = context_name
        self.wait_time = wait_time
        self.log_length = 0

        self.kubectl_client = KubectlClient(kubeconfig, context_name)

        apiclient = kubernetes_client(kubeconfig, context_name)
        self.coreV1Api = kubernetes.client.CoreV1Api(apiclient)
        self.appV1Api = kubernetes.client.AppsV1Api(apiclient)
        self.batchV1Api = kubernetes.client.BatchV1Api(apiclient)
        self.customObjectApi = kubernetes.client.CustomObjectsApi(apiclient)
        self.policyV1Api = kubernetes.client.PolicyV1Api(apiclient)
        self.networkingV1Api = kubernetes.client.NetworkingV1Api(apiclient)
        self.rbacAuthorizationV1Api = kubernetes.client.RbacAuthorizationV1Api(apiclient)
        self.storageV1Api = kubernetes.client.StorageV1Api(apiclient)
        self.schedulingV1Api = kubernetes.client.SchedulingV1Api(apiclient)
        self.resource_methods = {
            'pod': self.coreV1Api.list_namespaced_pod,
            'stateful_set': self.appV1Api.list_namespaced_stateful_set,
            'deployment': self.appV1Api.list_namespaced_deployment,
            'config_map': self.coreV1Api.list_namespaced_config_map,
            'service': self.coreV1Api.list_namespaced_service,
            'service_account': self.coreV1Api.list_namespaced_service_account,
            'pvc': self.coreV1Api.list_namespaced_persistent_volume_claim,
            'cronjob': self.batchV1Api.list_namespaced_cron_job,
            'ingress': self.networkingV1Api.list_namespaced_ingress,
            'network_policy': self.networkingV1Api.list_namespaced_network_policy,
            'pod_disruption_budget': self.policyV1Api.list_namespaced_pod_disruption_budget,
            'secret': self.coreV1Api.list_namespaced_secret,
            'endpoints': self.coreV1Api.list_namespaced_endpoints,
            'service_account': self.coreV1Api.list_namespaced_service_account,
            'job': self.batchV1Api.list_namespaced_job,
            'role': self.rbacAuthorizationV1Api.list_namespaced_role,
            'role_binding': self.rbacAuthorizationV1Api.list_namespaced_role_binding,
        }

    def run(self, input: dict, generation: int) -> Tuple[Snapshot, bool]:
        '''Simply run the cmd and dumps system_state, delta, operator log, events and input files without checking. 
           The function blocks until system converges.

        Args:
            cmd: subprocess command to be executed using subprocess.run

        Returns:
            result, err
        '''
        logger = get_thread_logger(with_prefix=True)

        self.operator_log_path = "%s/operator-%d.log" % (self.trial_dir, generation)
        self.system_state_path = "%s/system-state-%03d.json" % (self.trial_dir, generation)
        self.events_log_path = "%s/events.log" % (self.trial_dir)
        self.cli_output_path = "%s/cli-output-%d.log" % (self.trial_dir, generation)

        mutated_filename = '%s/mutated-%d.yaml' % (self.trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump(input, mutated_cr_file)

        cmd = ['apply', '-f', mutated_filename, '-n', self.namespace]

        cli_result = kubectl(cmd,
                             kubeconfig=self.kubeconfig,
                             context_name=self.context_name,
                             capture_output=True,
                             text=True)
        
        err = None
        try:
            err = self.wait_for_system_converge()
        except (KeyError, ValueError) as e:
            logger.error('Bug! Exception raised when waiting for converge.', exc_info=e)
            system_state = {}
            operator_log = 'Bug! Exception raised when waiting for converge.'

        logger.debug('STDOUT: ' + cli_result.stdout)
        logger.debug('STDERR: ' + cli_result.stderr)

        # when client API raise an exception, catch it and write to log instead of crashing Acto
        try:
            system_state = self.collect_system_state()
            operator_log = self.collect_operator_log()
            self.collect_events()
        except (KeyError, ValueError) as e:
            logger.error('Bug! Exception raised when waiting for converge.', exc_info=e)
            system_state = {}
            operator_log = 'Bug! Exception raised when waiting for converge.'

        snapshot = Snapshot(input, self.collect_cli_result(cli_result), system_state, operator_log)
        return snapshot, err

    def run_without_collect(self, seed_file: str):
        cmd = ['apply', '-f', seed_file, '-n', self.namespace]
        _ = kubectl(cmd, kubeconfig=self.kubeconfig, context_name=self.context_name)

        try:
            err = self.wait_for_system_converge()
        except (KeyError, ValueError) as e:
            logger.error('Bug! Exception raised when waiting for converge.', exc_info=e)
            system_state = {}
            operator_log = 'Bug! Exception raised when waiting for converge.'

    def delete(self, generation: int) -> bool:
        mutated_filename = '%s/mutated-%d.yaml' % (self.trial_dir, generation)
        logger.info('Deleting : ' + mutated_filename)
        
        cmd = ['delete', '-f', mutated_filename, '-n', self.namespace]
        cli_result = self.kubectl_client.kubectl(cmd, capture_output=True, text=True)
        logger.debug('STDOUT: ' + cli_result.stdout)
        logger.debug('STDERR: ' + cli_result.stderr)

        for tick in range(0, 600):
            crs = self.__get_custom_resources(self.namespace, self.crd_metainfo['group'],
                                        self.crd_metainfo['version'], self.crd_metainfo['plural'])
            if len(crs) == 0:
                break
            time.sleep(1)

        if len(crs) != 0:
            logger.error('Failed to delete custom resource.')
            return True
        else:
            logger.info(f'Successfully deleted custom resource in {tick}s.')
            return False

    def collect_system_state(self) -> dict:
        '''Queries resources in the test namespace, computes delta

        Args:
            result: includes the path to the resource state file
        '''
        logger = get_thread_logger(with_prefix=True)

        resources = {}

        for resource, method in self.resource_methods.items():
            resources[resource] = self.__get_all_objects(method)
            if resource == 'pod':
                # put pods managed by deployment / replicasets into an array
                all_pods = self.__get_all_objects(method)
                resources['deployment_pods'], resources['pod'] = group_pods(all_pods)
            elif resource == 'secret':
                resources[resource] = decode_secret_data(resources[resource])

        current_cr = self.__get_custom_resources(self.namespace, self.crd_metainfo['group'],
                                                 self.crd_metainfo['version'],
                                                 self.crd_metainfo['plural'])
        logger.debug(current_cr)

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
        logger = get_thread_logger(with_prefix=True)

        operator_pod_list = self.coreV1Api.list_namespaced_pod(
            namespace=self.namespace, watch=False, label_selector="acto/tag=operator-pod").items

        if len(operator_pod_list) >= 1:
            logger.debug('Got operator pod: pod name:' + operator_pod_list[0].metadata.name)
        else:
            logger.error('Failed to find operator pod')
            # TODO: refine what should be done if no operator pod can be found

        log = self.coreV1Api.read_namespaced_pod_log(name=operator_pod_list[0].metadata.name,
                                                     namespace=self.namespace)

        # only get the new log since previous result
        new_log = log.split('\n')
        new_log = new_log[self.log_length:]
        self.log_length += len(new_log)

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
        return cli_output

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

    def wait_for_system_converge(self, hard_timeout=600) -> bool:
        '''This function blocks until the system converges. It keeps 
           watching for incoming events. If there is no event within 
           60 seconds, the system is considered to have converged. 

        Args:
            hard_timeout: the maximal wait time for system convergence

        Returns:
            True if the system fails to converge within the hard timeout
        '''
        logger = get_thread_logger(with_prefix=True)

        start_timestamp = time.time()
        logger.info("Waiting for system to converge... ")

        event_stream = self.coreV1Api.list_namespaced_event(self.namespace,
                                                            _preload_content=False,
                                                            watch=True)

        combined_event_queue = Queue(maxsize=0)
        timer_hard_timeout = acto_timer.ActoTimer(hard_timeout, combined_event_queue, "timeout")
        watch_process = Process(target=self.watch_system_events,
                                args=(event_stream, combined_event_queue))

        timer_hard_timeout.start()
        watch_process.start()

        converge = True
        while (True):
            try:
                event = combined_event_queue.get(timeout=self.wait_time)
                if event == "timeout":
                    converge = False
                    break
            except queue.Empty:
                ready = True
                statefulsets = self.__get_all_objects(self.appV1Api.list_namespaced_stateful_set)
                deployments = self.__get_all_objects(self.appV1Api.list_namespaced_deployment)

                for sfs in statefulsets.values():
                    if sfs['status']['ready_replicas'] == None and sfs['status']['replicas'] == 0:
                        # replicas could be 0
                        continue
                    if sfs['status']['replicas'] != sfs['status']['ready_replicas']:
                        ready = False
                        logger.info("Statefulset %s is not ready yet" % sfs['metadata']['name'])
                        break

                for dp in deployments.values():
                    if dp['spec']['replicas'] == 0:
                        continue

                    if dp['status']['replicas'] != dp['status']['ready_replicas']:
                        ready = False
                        logger.info("Deployment %s is not ready yet" % dp['metadata']['name'])
                        break

                    for condition in dp['status']['conditions']:
                        if condition['type'] == 'Available' and condition['status'] != 'True':
                            ready = False
                            logger.info("Deployment %s is not ready yet" % dp['metadata']['name'])
                            break
                        elif condition['type'] == 'Progressing' and condition['status'] != 'True':
                            ready = False
                            logger.info("Deployment %s is not ready yet" % dp['metadata']['name'])
                            break

                if ready:
                    # only stop waiting if all deployments and statefulsets are ready
                    # else, keep waiting until ready or hard timeout
                    break

        event_stream.close()
        timer_hard_timeout.cancel()
        watch_process.terminate()

        time_elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - start_timestamp))
        if converge:
            logger.info('System took %s to converge' % time_elapsed)
            return False
        else:
            logger.error('System failed to converge within %d seconds' % hard_timeout)
            return True

    def watch_system_events(self, event_stream, queue: Queue):
        '''A process that watches namespaced events
        '''
        for _ in event_stream:
            try:
                queue.put("event")
            except (ValueError, AssertionError):
                pass


def decode_secret_data(secrets: dict) -> dict:
    '''Decodes secret's b64-encrypted data in the secret object
    '''
    logger = get_thread_logger(with_prefix=True)
    for secret in secrets:
        try:
            if 'data' in secrets[secret] and secrets[secret]['data'] != None:
                for key in secrets[secret]['data']:
                    secrets[secret]['data'][key] = base64.b64decode(
                        secrets[secret]['data'][key]).decode('utf-8')
        except Exception as e:
            # skip secret if decoding fails
            logger.error(e)
    return secrets


def group_pods(all_pods: dict) -> Tuple[dict, dict]:
    '''Groups pods into deployment pods and other pods

    For deployment pods, they are further grouped by their owner reference

    Return:
        Tuple of (deployment_pods, other_pods)
    '''
    deployment_pods = {}
    other_pods = {}
    for name, pod in all_pods.items():
        if 'acto/tag' in pod['metadata']['labels'] and pod['metadata']['labels'][
                'acto/tag'] == 'custom-oracle':
            # skip pods spawned by users' custom oracle
            continue
        elif pod['metadata']['owner_references'] != None:
            owner_reference = pod['metadata']['owner_references'][0]
            if owner_reference['kind'] == 'ReplicaSet' or owner_reference['kind'] == 'Deployment':
                owner_name = owner_reference['name']
                if owner_reference['kind'] == 'ReplicaSet':
                    # chop off the suffix of the ReplicaSet name to get the deployment name
                    owner_name = '-'.join(owner_name.split('-')[:-1])
                if owner_name not in deployment_pods:
                    deployment_pods[owner_name] = [pod]
                else:
                    deployment_pods[owner_name].append(pod)
            else:
                other_pods[name] = pod
        else:
            other_pods[name] = pod

    return deployment_pods, other_pods


# standalone runner for acto
if __name__ == "__main__":
    import argparse
    import sys
    import logging

    parser = argparse.ArgumentParser(description="Standalone runner for acto")
    parser.add_argument('-m',
                        '--manifest',
                        type=str,
                        help='path to the manifest file to be applied',
                        required=True)
    parser.add_argument('-c', '--context', type=str, help='path to the context file', required=True)
    parser.add_argument('-t',
                        '--trial-dir',
                        type=str,
                        help='path to the trial directory',
                        required=True)
    parser.add_argument('-g', '--generation', type=int, help='generation number', required=True)
    parser.add_argument('-k',
                        '--cluster-context-name',
                        type=str,
                        help='name of the cluster context',
                        required=True)
    args = parser.parse_args()

    # setting logging output to stdout
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    manifest = yaml.load(open(args.manifest, 'r'), Loader=yaml.FullLoader)
    context = json.load(open(args.context, 'r'))

    runner = Runner(context, args.trial_dir, args.cluster_context_name)

    runner.run(manifest, args.generation)
    print("Done")
