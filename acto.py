import argparse
import os
import kubernetes
import yaml
import time
import random
from datetime import datetime
from copy import deepcopy
import signal
import logging
from deepdiff import DeepDiff

from common import RunResult, get_diff_stat
import check_result

corev1Api = None
appv1Api = None
customObjectsApi = None
context = {'namespace': '', 'current_dir_path': ''}
workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')


def get_deployment_available_status(
        deployment: kubernetes.client.models.V1Deployment) -> bool:
    '''Get availability status from deployment condition

    Args:
        deployment: Deployment object in kubernetes

    Returns:
        if the deployment is available
    '''
    if deployment.status is None or deployment.status.conditions is None:
        return False

    for condition in deployment.status.conditions:
        if condition.type == 'Available' and condition.status == 'True':
            return True
    return False


def get_stateful_set_available_status(
        stateful_set: kubernetes.client.models.V1StatefulSet) -> bool:
    '''Get availability status from stateful set condition

    Args:
        stateful_set: stateful set object in kubernetes

    Returns:
        if the stateful set is available
    '''
    if stateful_set.status is None:
        return False
    if stateful_set.status.replicas > 0 and stateful_set.status.current_replicas == stateful_set.status.replicas:
        return True
    return False


def construct_kind_cluster():
    '''Delete kind cluster then create a new one
    '''
    os.system('kind delete cluster')

    kind_config_dir = 'kind_config'
    os.makedirs(kind_config_dir, exist_ok=True)
    kind_config_path = os.path.join(kind_config_dir, 'kind.yaml')

    with open(kind_config_path, 'w') as kind_config_file:
        kind_config_dict = {}
        kind_config_dict['kind'] = 'Cluster'
        kind_config_dict['apiVersion'] = 'kind.x-k8s.io/v1alpha4'
        kind_config_dict['nodes'] = []
        for _ in range(3):
            kind_config_dict['nodes'].append({'role': 'worker'})
        for _ in range(1):
            kind_config_dict['nodes'].append({'role': 'control-plane'})
        yaml.dump(kind_config_dict, kind_config_file)

    os.system('kind create cluster --config %s' % kind_config_path)

    kubernetes.config.load_kube_config()
    global corev1Api
    global appv1Api
    global customObjectsApi
    corev1Api = kubernetes.client.CoreV1Api()
    appv1Api = kubernetes.client.AppsV1Api()
    customObjectsApi = kubernetes.client.CustomObjectsApi()


def deploy_operator(operator_yaml_path: str):
    '''Deploy operator according to yaml

    Args:
        operator_yaml_path - path pointing to the operator yaml file
    '''
    global context
    with open(operator_yaml_path,'r') as operator_yaml, \
            open(os.path.join(workdir_path, 'new_operator.yaml'), 'w') as out_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        new_operator_documents = []
        for document in parsed_operator_documents:
            if document['kind'] == 'Deployment':
                document['metadata']['labels'][
                    'acto/tag'] = 'operator-deployment'
                document['spec']['template']['metadata']['labels'][
                    'acto/tag'] = 'operator-pod'
                context['namespace'] = document['metadata']['namespace']
            elif document['kind'] == 'StatefulSet':
                document['metadata']['labels'][
                    'acto/tag'] = 'operator-stateful-set'
                document['spec']['template']['metadata']['labels'][
                    'acto/tag'] = 'operator-pod'
                context['namespace'] = document['metadata']['namespace']
            elif document['kind'] == 'CustomResourceDefinition':
                # TODO: Handle multiple CRDs
                crd_data = {
                    'group': document['spec']['group'],
                    'plural': document['spec']['names']['plural'],
                    'version': document['spec']['versions'][0]
                               ['name'],  # TODO: Handle multiple versions
                }
                context['crd'] = crd_data
            new_operator_documents.append(document)
        yaml.dump_all(new_operator_documents, out_yaml)
        out_yaml.flush()
        os.system('kubectl apply -f %s' %
                  os.path.join(workdir_path, 'new_operator.yaml'))
        # os.system('cat <<EOF | kubectl apply -f -\n%s\nEOF' % yaml.dump_all(new_operator_documents))

        logging.debug('Deploying the operator, waiting for it to be ready')
        pod_ready = False
        for _ in range(60):
            operator_deployments = appv1Api.list_namespaced_deployment(
                context['namespace'],
                watch=False,
                label_selector='acto/tag=operator-deployment').items
            operator_stateful_states = appv1Api.list_namespaced_stateful_set(
                context['namespace'],
                watch=False,
                label_selector='acto/tag=operator-stateful-set').items
            operator_deployments_is_ready = len(operator_deployments) >= 1 \
                    and get_deployment_available_status(operator_deployments[0])
            operator_stateful_states_is_ready = len(operator_stateful_states) >= 1 \
                    and get_stateful_set_available_status(operator_stateful_states[0])
            if operator_deployments_is_ready or operator_stateful_states_is_ready:
                logging.debug('Operator ready')
                pod_ready = True
                break
            time.sleep(1)
        if not pod_ready:
            logging.error(
                "operator deployment failed to be ready within timeout")
            quit()


def deploy_dependency(yaml_paths):
    logging.debug('Deploying dependencies')
    for yaml_path in yaml_paths:
        os.system('kubectl apply -f %s' % yaml_path)
    if len(yaml_paths) > 0:
        time.sleep(30)  # TODO: how to wait smartly
    return


def construct_candidate_helper(node, node_path, result: dict):
    '''Recursive helper to flatten the candidate dict

    Args:
        node: current node
        node_path: path to access this node from root
        result: output dict
    '''
    if 'candidates' in node:
        result[node_path] = node['candidates']
    else:
        for child_key, child_value in node.items():
            construct_candidate_helper(child_value,
                                       '%s.%s' % (node_path, child_key), result)


def construct_candidate_from_yaml(yaml_path: str) -> dict:
    '''Constructs candidate dict from a yaml file
    
    Args:
        yaml_path: path of the input yaml file
        
    Returns:
        dict[JSON-like path]: list of candidate values
    '''
    with open(yaml_path, 'r') as input_yaml:
        doc = yaml.load(input_yaml, Loader=yaml.FullLoader)
        result = {}
        construct_candidate_helper(doc, '', result)
        return result


def elect_mutation_parameter(candidates_dict: dict):
    '''method for electing the parameter to mutate and which value to pick
    
    Args:
        candidates_dict: flat dictionary specifying list of valid values for each parameter

    Returns:
        (path, value)
    '''
    random_entry = random.choice(list(candidates_dict.items()))
    return random_entry[0], random.choice(random_entry[1])


def mutate_application_spec(current_spec: dict, candidates: dict):
    '''mutate one of the fields in current spec according to candidates dict
    
    Args:
        current_spec: last spec that fed to operator
        candidates: flat dictionary specifying list of valid values for each parameter
    '''
    path, v = elect_mutation_parameter(candidates)
    logging.debug('Elected parameter [%s]' % path)
    logging.debug('Elected value: %s' % v)
    current_node = current_spec
    key_list = [x for x in path.split('.') if x]
    for key in key_list[:-1]:
        current_node = current_node[key]
    current_node[key_list[-1]] = v
    return current_spec


def run_trial(initial_input: dict,
              candidate_dict: dict,
              trial_num: int,
              num_mutation: int = 100):
    '''Run a trial starting with the initial input, mutate with the candidate_dict, and mutate for num_mutation times
    
    Args:
        initial_input: the initial input without mutation
        candidate_dict: guides the mutation
        trial_num: how many trials have been run
        num_mutation: how many mutations to run at each trial
    '''
    trial_dir = os.path.join(workdir_path, str(trial_num))
    os.makedirs(trial_dir, exist_ok=True)
    global context
    context['current_dir_path'] = trial_dir

    checker = check_result.Checker(context, trial_dir, corev1Api, appv1Api,
                                   customObjectsApi)
    current_cr = deepcopy(initial_input)

    generation = 0
    while generation < num_mutation:
        parent_cr = deepcopy(current_cr)
        if generation != 0:
            mutate_application_spec(current_cr, candidate_dict)

        cr_diff = DeepDiff(parent_cr,
                           current_cr,
                           ignore_order=True,
                           report_repetition=True,
                           view='tree')
        if len(cr_diff) == 0 and generation != 0:
            logging.info('CR unchanged, continue')
            continue

        mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump(current_cr, mutated_cr_file)

        retval = checker.run_and_check(
            ['kubectl', 'apply', '-f', mutated_filename],
            cr_diff,
            generation=generation)
        generation += 1

        if retval == RunResult.invalidInput:
            # Revert to parent CR
            current_cr = parent_cr
        elif retval == RunResult.unchanged:
            continue
        elif retval == RunResult.error:
            # We found an error!
            logging.info('Diff stat: %s ' % get_diff_stat())
            return
        elif retval == RunResult.passing:
            continue
        else:
            logging.error('Unknown return value, abort')
            quit()


def timeout_handler(sig, frame):
    raise TimeoutError


if __name__ == '__main__':
    start_time = time.time()

    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
    parser.add_argument('--candidates',
                        '-c',
                        dest='candidates',
                        required=True,
                        help="yaml file to specify candidates for parameters")
    parser.add_argument('--seed',
                        '-s',
                        dest='seed',
                        required=True,
                        help="seed CR file")
    parser.add_argument('--operator',
                        '-o',
                        dest='operator',
                        required=True,
                        help="yaml file for deploying the operator")
    parser.add_argument('--duration',
                        '-d',
                        dest='duration',
                        default=6,
                        help='Number of hours to run')

    args = parser.parse_args()

    os.makedirs(workdir_path, exist_ok=True)
    logging.basicConfig(filename=os.path.join(workdir_path, 'test.log'),
                        level=logging.DEBUG,
                        filemode='w',
                        format='%(levelname)s, %(name)s, %(message)s')
    logging.getLogger("kubernetes").setLevel(logging.ERROR)

    candidate_dict = construct_candidate_from_yaml(args.candidates)
    logging.debug(candidate_dict)

    application_cr: dict
    try:
        with open(args.seed, 'r') as cr_file:
            application_cr = yaml.load(cr_file, Loader=yaml.FullLoader)
    except:
        logging.error('Failed to read cr yaml, aborting')
        quit()

    # register timeout to automatically stop after # hours
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(args.duration) * 60 * 60)

    trial_num = 0
    while True:
        trial_start_time = time.time()
        construct_kind_cluster()
        deploy_operator(args.operator)
        deploy_dependency([])
        run_trial(application_cr, candidate_dict, trial_num)
        trial_elapsed = time.strftime(
            "%H:%M:%S", time.gmtime(time.time() - trial_start_time))
        logging.info('Trial %d finished, completed in %s' %
                     (trial_num, trial_elapsed))
        trial_num = trial_num + 1