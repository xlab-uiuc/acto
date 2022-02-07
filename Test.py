import argparse
from distutils import core
import os
import kubernetes
import yaml
import time
import random
from datetime import datetime
from copy import deepcopy
import signal

from common import p_debug, p_error, RunResult
import check_result

corev1 = None
appv1 = None
metadata = {'namespace': '',
            'current_dir_path': ''}
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
    global corev1
    global appv1
    corev1 = kubernetes.client.CoreV1Api()
    appv1 = kubernetes.client.AppsV1Api()


def deploy_operator(operator_yaml_path: str):
    '''Deploy operator according to yaml

    Args:
        operator_yaml_path - path pointing to the operator yaml file
    '''
    global metadata
    with open(operator_yaml_path,'r') as operator_yaml, \
            open('new_operator.yaml', 'w') as out_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        new_operator_documents = []
        for document in parsed_operator_documents:
            if document['kind'] == 'Deployment':
                document['metadata']['labels'][
                    'testing/tag'] = 'operator-deployment'
                document['spec']['template']['metadata']['labels'][
                    'testing/tag'] = 'operator-pod'
                metadata['namespace'] = document['metadata']['namespace']
            new_operator_documents.append(document)
        yaml.dump_all(new_operator_documents, out_yaml)
        out_yaml.flush()
        os.system('kubectl apply -f %s' % 'new_operator.yaml')
        # os.system('cat <<EOF | kubectl apply -f -\n%s\nEOF' % yaml.dump_all(new_operator_documents))

        p_debug('Deploying the operator, waiting for it to be ready')
        pod_ready = False
        for _ in range(60):
            operator_deployments = appv1.list_namespaced_deployment(
                metadata['namespace'],
                watch=False,
                label_selector='testing/tag=operator-deployment').items
            if len(operator_deployments) >= 1 \
                    and get_deployment_available_status(operator_deployments[0]):
                p_debug('Operator ready')
                pod_ready = True
                break
            time.sleep(1)
        if not pod_ready:
            p_error("operator deployment failed to be ready within timeout")
            quit()


def deploy_dependency(yaml_paths):
    p_debug('Deploying dependencies')
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
    p_debug('Elected parameter [%s]' % path)
    p_debug('Elected value: %s' % v)
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
    global metadata
    metadata['current_dir_path'] = trial_dir

    current_cr = deepcopy(initial_input)
    for generation in range(num_mutation):
        parent_cr = deepcopy(current_cr)
        mutate_application_spec(current_cr, candidate_dict)
        mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump(current_cr, mutated_cr_file)

        retval = check_result.run_and_check(
            ['kubectl', 'apply', '-f', mutated_filename],
            metadata,
            generation=generation)

        if retval == RunResult.invalidInput:
            # Revert to parent CR
            application_cr = parent_cr
        elif retval == RunResult.unchanged:
            continue
        elif retval == RunResult.error:
            # We found an error!
            return
        elif retval == RunResult.passing:
            continue
        else:
            p_error('Unknown return value, abort')
            quit()


def timeout_handler():
    raise TimeoutError


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Continuous testing')

    candidate_dict = construct_candidate_from_yaml('rabbitmq_candidates.yaml')
    p_debug(candidate_dict)

    application_cr: dict
    try:
        with open('rabbitmq_example_cr.yaml', 'r') as cr_file:
            application_cr = yaml.load(cr_file, Loader=yaml.FullLoader)
    except:
        p_error('Failed to read cr yaml, aborting')
        quit()

    os.makedirs(workdir_path, exist_ok=True)

    # register timeout to automatically stop after 12 hours
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(12 * 60 * 60)

    trial_num = 0
    while True:
        construct_kind_cluster()
        deploy_operator('cluster-operator.yml')
        deploy_dependency([])
        run_trial(application_cr, candidate_dict, trial_num)
        trial_num = trial_num + 1