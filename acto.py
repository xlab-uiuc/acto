import argparse
import subprocess
import os
import kubernetes
from kubernetes.client import models, AppsV1Api, ApiextensionsV1Api
import yaml
import time
from typing import List, Tuple, Optional
import random
from datetime import datetime
from copy import deepcopy
import signal
import logging
from deepdiff import DeepDiff
from common import *
import check_result
import schema
import value_with_schema

context = {
    'namespace': '',
    'current_dir_path': '',
    'preload_images': [],
}
test_summary = {}
workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')
ACTO_NAMESPACE = "acto-namespace"


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


def get_namespaced_resources() -> Tuple[List[str], List[str]]:
    '''Get namespaced and non-namespaced available resources list

    Returns:
        list of namespaced kind and list of non-namespaced kind
    '''
    namespaced_resources = []
    non_namespaced_resources = []
    appv1Api = kubernetes.client.AppsV1Api()
    for resource in appv1Api.get_api_resources().resources:
        if resource.namespaced:
            namespaced_resources.append(resource.kind)
        else:
            non_namespaced_resources.append(resource.kind)
    return namespaced_resources, non_namespaced_resources


def deploy_operator(operator_yaml: str):
    '''Deploy operator according to yaml
    '''
    cmd = ['kubectl', 'apply', '-f', operator_yaml]
    cli_result = subprocess.run(cmd, capture_output=True, text=True)
    # logging.debug('Operator deploy STDOUT: %s' % cli_result.stdout)
    # logging.debug('Operator deploy STDERR: %s' % cli_result.stderr)

    logging.debug('Deploying the operator, waiting for it to be ready')
    pod_ready = False
    appv1Api = kubernetes.client.AppsV1Api()
    operator_stateful_states = []
    for tick in range(90):
        # get all deployment and stateful set.
        operator_deployments = appv1Api.list_namespaced_deployment(
            context['namespace'],
            watch=False).items
        operator_stateful_states = appv1Api.list_namespaced_stateful_set(
            context['namespace'],
            watch=False).items
        # TODO: we should check all deployment and stateful set are ready
        operator_deployments_is_ready = len(operator_deployments) >= 1 \
                and get_deployment_available_status(operator_deployments[0])
        operator_stateful_states_is_ready = len(operator_stateful_states) >= 1 \
                and get_stateful_set_available_status(operator_stateful_states[0])
        if operator_deployments_is_ready or operator_stateful_states_is_ready:
            logging.debug('Operator ready')
            pod_ready = True
            break
        time.sleep(1)
    logging.info('Operator took %d seconds to get ready' % tick)
    if not pod_ready:
        logging.error("operator deployment failed to be ready within timeout")
        return False
    else:
        return True


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


def prune_noneffective_change(diff):
    '''
    This helper function handles the corner case where an item is added to
    dictionary, but the value assigned is null, which makes the change 
    meaningless
    '''
    if 'dictionary_item_added' in diff:
        for item in diff['dictionary_item_added']:
            if item.t2 == None:
                diff['dictionary_item_added'].remove(item)
        if len(diff['dictionary_item_added']) == 0:
            del diff['dictionary_item_added']


def run_trial(initial_input: dict,
              candidate_dict: dict,
              trial_num: int,
              num_mutation: int = 100) -> Tuple[ErrorResult, int]:
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

    checker = check_result.Checker(context, trial_dir)
    current_cr = deepcopy(initial_input)
    spec_with_schema = value_with_schema.attach_schema_to_value(
        current_cr['spec'], context['crd']['spec_schema'])

    generation = 0
    while generation < num_mutation:
        parent_cr = deepcopy(current_cr)
        if generation != 0:
            # mutate_application_spec(current_cr, candidate_dict)
            spec_with_schema.mutate()
            current_cr['spec'] = spec_with_schema.raw_value()

        cr_diff = DeepDiff(parent_cr,
                           current_cr,
                           ignore_order=True,
                           report_repetition=True,
                           view='tree')
        prune_noneffective_change(cr_diff)
        if len(cr_diff) == 0 and generation != 0:
            logging.info('CR unchanged, continue')
            continue

        mutated_filename = '%s/mutated-%d.yaml' % (trial_dir, generation)
        with open(mutated_filename, 'w') as mutated_cr_file:
            yaml.dump(current_cr, mutated_cr_file)

        result = checker.run_and_check(
            ['kubectl', 'apply', '-f', mutated_filename],
            cr_diff,
            generation=generation)
        generation += 1

        if isinstance(result, InvalidInputResult):
            # Revert to parent CR
            current_cr = parent_cr
            spec_with_schema = value_with_schema.attach_schema_to_value(
                current_cr['spec'], context['crd']['spec_schema'])
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

    return None, generation


def process_operator_yaml(operator_yaml_path: str):
    '''Process the operator deployment yaml file

    Extract the information needed later, including namespace, image, and CRD
    Attach tag to operator so that we can identify it later

    Args:
        operator_yaml_path: path of the yaml file for deploying the operator

    Modifies global context
    '''
    global context
    namespaced_resources, _ = get_namespaced_resources()
    new_operator_path = os.path.join(workdir_path, 'new_operator.yaml')
    with open(operator_yaml_path,'r') as operator_yaml, \
            open(new_operator_path, 'w') as out_yaml:
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        new_operator_documents = []
        for document in parsed_operator_documents:
            # set namespace to default if not specify
            if document['kind'] in namespaced_resources \
                    and 'namespace' not in document['metadata']:
                document['metadata']['namespace'] = 'default'
            if document['kind'] == 'Deployment':
                document['metadata']['labels']['acto/tag'] \
                    = 'operator-deployment'
                document['spec']['template']['metadata']['labels']['acto/tag'] \
                    = 'operator-pod'

                context['namespace'] = document['metadata']['namespace']
                context['preload_images'].append(
                    document['spec']['template']['spec']['containers'][0]
                    ['image'])
            elif document['kind'] == 'StatefulSet':
                document['metadata']['labels']['acto/tag'] \
                    = 'operator-stateful-set'
                document['spec']['template']['metadata']['labels']['acto/tag'] \
                    = 'operator-pod'

                context['namespace'] = document['metadata']['namespace']
            elif document['kind'] == 'CustomResourceDefinition':
                # TODO: Handle multiple CRDs
                crd_data = {
                    'group':
                        document['spec']['group'],
                    'plural':
                        document['spec']['names']['plural'],
                    'version':
                        document['spec']['versions'][0]
                        ['name'],  # TODO: Handle multiple versions
                    'spec_schema':
                        schema.extract_schema(
                            ['root'], document['spec']['versions'][0]['schema']
                            ['openAPIV3Schema']['properties']['spec'])
                }
                context['crd'] = crd_data
            new_operator_documents.append(document)
        yaml.dump_all(new_operator_documents, out_yaml)
    context['operator_yaml'] = new_operator_path


def preload_images():
    '''Preload some frequently used images into Kind cluster to avoid ImagePullBackOff

    Uses global context
    '''
    if len(context['preload_images']) == 0:
        logging.error(
            'No image to preload, we at least should have operator image')

    for image in context['preload_images']:
        p = subprocess.run(['kind', 'load', 'docker-image', image])
        if p.returncode != 0:
            logging.info('Image not present local, pull and retry')
            os.system('docker pull %s' % image)
            p = subprocess.run(['kind', 'load', 'docker-image', image])


def process_crd(crd_name: Optional[str] = None):
    ''' Get crd from k8s and set context['crd']

    When there are more than one crd in the cluster, user should set crd_name
    '''
    global context
    apiextensionsV1Api = ApiextensionsV1Api()
    crds: List[models.V1CustomResourceDefinition] = apiextensionsV1Api.list_custom_resource_definition().items
    crd: Optional[models.V1CustomResourceDefinition] = None
    if len(crds) == 0:
        logging.error(
            'No crd is found')
        quit()
    elif len(crds) == 1:
        crd = crds[0]
    elif crd_name:
        # TODO: loop over crd and find name=crd_name
        crd = crds[0]
    else:
        logging.error(
            'There are multiple crds, please specify parameter [crd_name]')
        quit()
    if crd:
        # there is openAPIV3Schema schema issue when using python k8s client, need to fetch data from cli
        crd_result = subprocess.run(
            ['kubectl', 'get', 'crd', crd.metadata.name, "-o", "json"], capture_output=True, text=True)
        crd_obj = json.loads(crd_result.stdout)
        spec: models.V1CustomResourceDefinitionSpec = crd.spec
        crd_data = {
            'group': spec.group,
            'plural': spec.names.plural,
            'version': spec.versions[0].name,  # TODO: Handle multiple versions
            'spec_schema':
                schema.extract_schema(
                    ['root'], crd_obj['spec']['versions'][0]['schema']['openAPIV3Schema']['properties']['spec'])
        }
        context['crd'] = crd_data


def add_acto_label():
    '''Add acto label to deployment, stateful_state and corresponding pods.
    '''
    appv1Api = AppsV1Api()
    operator_deployments = appv1Api.list_namespaced_deployment(
        context['namespace'],
        watch=False).items
    operator_stateful_states = appv1Api.list_namespaced_stateful_set(
        context['namespace'],
        watch=False).items
    for deployment in operator_deployments:
        patches = [
            {"metadata": {"labels": {"acto/tag": "operator-deployment"}}},
            {"spec": {"template": {"metadata": {"labels": {"acto/tag": "operator-pod"}}}}}
        ]
        for patch in patches:
            appv1Api.patch_namespaced_deployment(
                deployment.metadata.name, deployment.metadata.namespace, patch)
    for stateful_state in operator_stateful_states:
        patches = [
            {"metadata": {"labels": {"acto/tag": "operator-stateful-set"}}},
            {"spec": {"template": {"metadata": {"labels": {"acto/tag": "operator-pod"}}}}}
        ]
        for patch in patches:
            appv1Api.patch_namespaced_stateful_set(
                stateful_state.metadata.name, deployment.metadata.namespace, patch)


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
    parser.add_argument('--preload-images',
                        dest='preload_images',
                        nargs='*',
                        help='Docker images to preload into Kind cluster')

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

    # Preload frequently used images to amid ImagePullBackOff
    if args.preload_images:
        context['preload_images'].extend(args.preload_images)
        logging.info('%s will be preloaded into Kind cluster', args.preload_images)

    # register timeout to automatically stop after # hours
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(args.duration) * 60 * 60)

    trial_num = 0
    while True:
        trial_start_time = time.time()
        construct_kind_cluster()
        preload_images()
        succeed = deploy_operator(args.operator)
        if not succeed:
            continue
        process_crd()
        add_acto_label()
        deploy_dependency([])
        trial_err, num_tests = run_trial(application_cr, candidate_dict,
                                         trial_num)

        trial_elapsed = time.strftime(
            "%H:%M:%S", time.gmtime(time.time() - trial_start_time))
        logging.info('Trial %d finished, completed in %s' %
                     (trial_num, trial_elapsed))
        logging.info('---------------------------------------\n')

        result_dict = {}
        result_dict['trial_num'] = trial_num
        result_dict['duration'] = trial_elapsed
        result_dict['num_tests'] = num_tests
        if trial_err == None:
            logging.info('Trial %d completed without error')
        else:
            result_dict['oracle'] = trial_err.oracle
            result_dict['message'] = trial_err.message
            result_dict['input_delta'] = trial_err.input_delta
            result_dict['matched_system_delta'] = trial_err.matched_system_delta
        result_path = os.path.join(context['current_dir_path'], 'result.json')
        with open(result_path, 'w') as result_file:
            json.dump(result_dict, result_file, cls=ActoEncoder, indent=6)
        trial_num = trial_num + 1