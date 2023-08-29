import base64
import queue
import time
from multiprocessing import Process, Queue

import yaml

import acto.utils.acto_timer as acto_timer
from acto.common import *
from acto.kubernetes_io import KubectlClient
from acto.kubernetes_io.kubernetes_exporter import KubernetesExporter
from acto.serialization import ActoEncoder
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger


class Runner(object):

    def __init__(self,
                 context: dict,
                 trial_dir: str,
                 kubeconfig: str,
                 context_name: str,
                 wait_time: int = 45):
        self.namespace = context["namespace"]
        self.crd_metainfo: dict = context['crd']
        self.trial_dir = trial_dir
        self.kubeconfig = kubeconfig
        self.context_name = context_name
        self.wait_time = wait_time

        self.kubectl_client = KubectlClient(kubeconfig, context_name)
        self.kube_exporter = KubernetesExporter(namespace=self.namespace,
                                                kubectl_client=self.kubectl_client,
                                                crd_meta_info=self.crd_metainfo)
        # TODO: remove these two apis in future commits
        # because we will move wait_system_converge out of the file
        self.coreV1Api = self.kube_exporter.coreV1Api
        self.appV1Api = self.kube_exporter.appV1Api

    def run(self, input: dict, generation: int) -> Tuple[Snapshot, bool]:
        '''Simply run the cmd and dumps system_state, delta, operator log, events and input files without checking. 
           The function blocks until system converges.

        Args:

        Returns:
            result, err
        '''
        logger = get_thread_logger(with_prefix=True)

        self.operator_log_path = "%s/operator-%d.log" % (self.trial_dir, generation)
        self.system_state_path = "%s/system-state-%03d.json" % (self.trial_dir, generation)
        self.events_log_path = "%s/events-%d.json" % (self.trial_dir, generation)
        self.cli_output_path = "%s/cli-output-%d.log" % (self.trial_dir, generation)
        self.not_ready_pod_log_path = "{}/not-ready-pod-{}-{{}}.log".format(self.trial_dir, generation)

        mutated_filename = '%s/mutated-%d.yaml' % (self.trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump(input, mutated_cr_file)

        cmd = ['apply', '-f', mutated_filename, '-n', self.namespace]

        cli_result = self.kubectl_client.kubectl(cmd, capture_output=True, text=True)
        logger.debug('STDOUT: ' + cli_result.stdout)
        logger.debug('STDERR: ' + cli_result.stderr)

        if cli_result.returncode != 0:
            logger.error('kubectl apply failed with return code %d' % cli_result.returncode)
            logger.error('STDOUT: ' + cli_result.stdout)
            logger.error('STDERR: ' + cli_result.stderr)
            return Snapshot(input, self.collect_cli_result(cli_result), {}, []), True
        err = None
        try:
            err = self.wait_for_system_converge()
        except (KeyError, ValueError) as e:
            logger.error('Bug! Exception raised when waiting for converge.', exc_info=e)
            system_state = {}
            operator_log = 'Bug! Exception raised when waiting for converge.'
            err = True

        # when client API raise an exception, catch it and write to log instead of crashing Acto
        try:
            system_state = self.kube_exporter.collect_system_state()
            # Dump system state
            with open(self.system_state_path, 'w') as fout:
                json.dump(system_state, fout, cls=ActoEncoder, indent=6)
            operator_log = self.kube_exporter.collect_operator_log()
            with open(self.operator_log_path, 'a') as f:
                for line in operator_log:
                    f.write("%s\n" % line)
            events = self.kube_exporter.collect_events()
            with open(self.events_log_path, 'w') as f:
                f.write(json.dumps(events))
            unsaved = self.kube_exporter.collect_not_ready_pods_logs()
            # TODO: Fix unsaved not_ready_pods_logs
        except (KeyError, ValueError) as e:
            logger.error('Bug! Exception raised when waiting for converge.', exc_info=e)
            system_state = {}
            operator_log = 'Bug! Exception raised when waiting for converge.'
            err = True

        snapshot = Snapshot(input, self.collect_cli_result(cli_result), system_state, operator_log)
        return snapshot, err

    def run_without_collect(self, seed_file: str):
        cmd = ['apply', '-f', seed_file, '-n', self.namespace]
        _ = self.kubectl_client.kubectl(cmd)

        try:
            err = self.wait_for_system_converge()
        except (KeyError, ValueError) as e:
            logger = get_thread_logger(with_prefix=True)
            logger.error('Bug! Exception raised when waiting for converge.', exc_info=e)
            system_state = {}
            operator_log = 'Bug! Exception raised when waiting for converge.'


    def collect_cli_result(self, p: subprocess.CompletedProcess):
        cli_output = {}
        cli_output["stdout"] = p.stdout.strip()
        cli_output["stderr"] = p.stderr.strip()
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


    def wait_for_system_converge(self, hard_timeout=480) -> bool:
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
                    if sfs['spec']['replicas'] != sfs['status']['replicas']:
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


# standalone runner for acto
if __name__ == "__main__":
    import argparse
    import logging
    import sys

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
