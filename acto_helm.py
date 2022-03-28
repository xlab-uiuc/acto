import argparse
import json
import os
import kubernetes
import yaml
import time
from typing import List, Tuple
import random
from datetime import datetime
from copy import deepcopy
import signal
import logging
from deepdiff import DeepDiff
import sh
from common import *
import check_result
from rich.console import Console

console = Console()
context = {}
workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')
ACTO_NAMESPACE = "acto-namespace"

def construct_kind_cluster(k8s_version: str):
    '''Delete kind cluster then create a new one
    '''
    console.log("Deleting Kind Cluster")
    sh.kind("delete", "cluster")
    console.log("Kind Cluster Deleted")

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

    console.log("Installing Kind Cluster")
    sh.kind("create", "cluster", config=kind_config_path, image=f"kindest/node:v{k8s_version}")
    console.log("Kind Cluster Installed")
    kubernetes.config.load_kube_config()

def deploy_init_yml_file(init_yml: str):
    """
    Deploy an yaml file before operator deployment. 
    For example, cass-operator requires an StorageClass as dependency.
    """
    if init_yml:
        console.log("Apply init yml")
        sh.kubectl("apply", filename=init_yml)
        console.log("Init yml applied")
    else:
        console.log("No init yml")

def deploy_operator_helm_chart(operator_helm_chart: str, crd_yaml: str):
    # TODO: Check whether the helm chart has the label "acto/tag: operator-pod" for operator Pod or not
    
    # Install operator, CRD, RBAC, and so on.
    # --wait: https://helm.sh/docs/helm/helm_upgrade/
    console.log("Installing helm chart dependency")
    sh.helm("dependency", "build", operator_helm_chart)
    console.log("Installing helm chart")
    sh.helm("install", "acto-test-operator", "--create-namespace", operator_helm_chart, wait=True, timeout="3m", namespace=ACTO_NAMESPACE)
    console.log("Get helm chart result")
    helm_ls_result = sh.helm("ls", o="json", all_namespaces=True, all=True)
    try:
        helm_release = json.loads(helm_ls_result.stdout)[0]
    except Exception:
        console.log("Failed to get helm chart's status", style="bold red")
        quit()

    if helm_release["status"] != "deployed":
        console.log("Helm chart deployment failed to be ready within timeout", style="bold red")
        quit()

    # TODO (Kai-Hsun): This is not a good practice. It's better to use k8s API to get CRD info.
    global context
    context['namespace'] = helm_release['namespace']

    with open(crd_yaml, 'r') as input_yaml:
        crd_info = yaml.load(input_yaml, Loader=yaml.FullLoader)
        context['crd'] = {
            'group': crd_info['spec']['group'],
            'plural': crd_info['spec']['names']['plural'],
            'version': crd_info['spec']['versions'][0]['name'],  # TODO: Handle multiple versions
            'kind': crd_info['spec']['names']['kind'],
        }

    # TODO (Kai-Hsun):
    # We can use the following commands to get operator log
    # Step1: kubectl get all --all-namespaces -l='app.kubernetes.io/managed-by=Helm'
    #   NAMESPACE   NAME                                          READY   UP-TO-DATE   AVAILABLE   AGE
    #   default     deployment.apps/mongodb-kubernetes-operator   1/1     1            1           30m
    # 
    # Step2: kubectl logs deployment/mongodb-kubernetes-operator
    # 
    # Other Methods:
    # (1) the deployment will create a replicaset, and we can also collect logs by: 
    #        kubectl logs replicaset/mongodb-kubernetes-operator-779c476757
    # (2) the replicaset => Controlled By:  Deployment/mongodb-kubernetes-operator
    #     operator pod   => Controlled By:  ReplicaSet/mongodb-kubernetes-operator-779c476757
    # => We can also find the operator pod by method (2)

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


def run_trial(initial_input: list,
              candidate_dict: dict,
              trial_num: int,
              num_mutation: int = 100) -> Tuple[ErrorResult, int]:
    '''Run a trial starting with the initial input, mutate with the candidate_dict, and mutate for num_mutation times
    
    Args:
        initial_input: the initial input without mutation 
            (A CR yaml may contain more than 1 resource, and thus initial_input is a list. (ex: MongoDB))
        candidate_dict: guides the mutation
        trial_num: how many trials have been run
        num_mutation: how many mutations to run at each trial
    '''
    trial_dir = os.path.join(workdir_path, str(trial_num))
    os.makedirs(trial_dir, exist_ok=True)
    
    checker = check_result.Checker(context, trial_dir)

    cr_yaml = list(filter(lambda resource: resource.get("kind", "") == context['crd']['kind'], initial_input))[0]
    remain_yaml_list = list(filter(lambda resource: resource.get("kind", "") != context['crd']['kind'], initial_input))
    current_cr = deepcopy(cr_yaml)

    generation = 0
    while generation < num_mutation:
        console.log(f"Run Trial {generation}")
        parent_cr = deepcopy(current_cr)
        if generation != 0:
            mutate_application_spec(current_cr, candidate_dict)
        cr_diff = DeepDiff(parent_cr,
                           current_cr,
                           ignore_order=True,
                           report_repetition=True,
                           view='tree')
        if len(cr_diff) == 0 and generation != 0:
            console.log("CR unchanged, continue")
            logging.info('CR unchanged, continue')
            continue

        mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump_all([current_cr] + remain_yaml_list, mutated_cr_file)
        result = checker.run_and_check(
            ['kubectl', 'apply', '-n', ACTO_NAMESPACE, '-f', mutated_filename],
            cr_diff,
            generation=generation)
        generation += 1
        console.log(f"Trial {generation} - {result}")
        if isinstance(result, InvalidInputResult):
            # Revert to parent CR
            current_cr = parent_cr
            # TODO: handle spec_with_schema: https://github.com/xlab-uiuc/acto/commit/d670db83928d791e13e57294d2d569ee01c7e76f
            # spec_with_schema = value_with_schema.attach_schema_to_value(
            #     current_cr['spec'], context['crd']['spec_schema'])
        elif isinstance(result, UnchangedInputResult):
            continue
        elif isinstance(result, ErrorResult):
            # We found an error!
            return result, generation
        elif isinstance(result, PassResult):
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
    parser.add_argument('--duration',
                        '-d',
                        dest='duration',
                        default=6,
                        help='Number of hours to run')
    parser.add_argument('--helm',
                        dest='operator_chart',
                        required=True,
                        help='Path of operator helm chart')
    parser.add_argument('--crd',
                        dest='crd',
                        required=True,
                        help='Path of CRD yaml file')
    parser.add_argument('--init',
                        dest='init',
                        required=False,
                        help='Path of init yaml file (deploy before operator)')
    args = parser.parse_args()

    os.makedirs(workdir_path, exist_ok=True)
    logging.basicConfig(filename=os.path.join(workdir_path, 'test.log'),
                        level=logging.DEBUG,
                        filemode='w',
                        format='%(levelname)s, %(name)s, %(message)s')
    logging.getLogger("kubernetes").setLevel(logging.ERROR)

    candidate_dict = construct_candidate_from_yaml(args.candidates)
    logging.debug(candidate_dict)

    cr_resource_list = []
    try:
        with open(args.seed, 'r') as cr_file:
            cr_resource_list = list(yaml.load_all(cr_file, Loader=yaml.FullLoader))
    except:
        logging.error('Failed to read cr yaml, aborting')
        quit()

    # register timeout to automatically stop after # hours
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(args.duration) * 60 * 60)

    trial_num = 0

    while True:
        trial_start_time = time.time()
        construct_kind_cluster("1.20.15")
        deploy_init_yml_file(args.init)
        deploy_operator_helm_chart(args.operator_chart, args.crd)
        run_trial(cr_resource_list, candidate_dict, trial_num)
        trial_elapsed = time.strftime(
            "%H:%M:%S", time.gmtime(time.time() - trial_start_time))
        logging.info('Trial %d finished, completed in %s' %
                     (trial_num, trial_elapsed))
        trial_num = trial_num + 1
