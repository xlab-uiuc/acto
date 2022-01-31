import argparse
from distutils.log import error
import os
import kubernetes
import yaml
import time
import typing
import random


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
    os.system('kind create cluster')


def deploy_operator(operator_yaml_path: str):
    '''Deploy operator according to yaml

    Args:
        operator_yaml_path - path pointing to the operator yaml file
    '''
    with open(operator_yaml_path,'r') as operator_yaml, \
            open('new_operator.yaml', 'w') as out_yaml:
        namespace = str()
        parsed_operator_documents = yaml.load_all(operator_yaml,
                                                  Loader=yaml.FullLoader)
        new_operator_documents = []
        for document in parsed_operator_documents:
            if document['kind'] == 'Deployment':
                document['metadata']['labels']['testing/tag'] = 'testing'
                namespace = document['metadata']['namespace']
            new_operator_documents.append(document)
        yaml.dump_all(new_operator_documents, out_yaml)
        out_yaml.flush()
        os.system('kubectl apply -f %s' % 'new_operator.yaml')
        # os.system('cat <<EOF | kubectl apply -f -\n%s\nEOF' % yaml.dump_all(new_operator_documents))

        kubernetes.config.load_kube_config()
        corev1 = kubernetes.client.CoreV1Api()
        appv1 = kubernetes.client.AppsV1Api()

        print('Deploying the operator, waiting for it to be ready')
        pod_ready = False
        for _ in range(60):
            operator_deployments = appv1.list_namespaced_deployment(
                namespace, watch=False,
                label_selector='testing/tag=testing').items
            if len(operator_deployments) >= 1 \
                    and get_deployment_available_status(operator_deployments[0]):
                print('Operator ready')
                pod_ready = True
                break
            time.sleep(1)
        if not pod_ready:
            error("operator deployment failed to be ready within timeout")


def deploy_dependency(yaml_paths):
    for yaml_path in yaml_paths:
        os.system('kubectl apply -f %s' % yaml_path)
    time.sleep(30) # TODO: how to wait smartly
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
            construct_candidate_helper(child_value, '%s.%s' % (node_path, child_key), result)


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
    current_node = current_spec
    key_list = [x for x in path.split('.') if x]
    for key in key_list[:-1]:
        current_node = current_node[key]
    current_node[key_list[-1]] = v
    return current_spec


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Continuous testing')

    construct_kind_cluster()
    deploy_operator('cluster-operator.yml')
    deploy_dependency([])
    candidate_dict = construct_candidate_from_yaml('rabbitmq_candidates.yaml')
    print(candidate_dict)

    # while True:
    #     mutate_application_spec()
    #     # TODO: submit to operator
    #     # TODO: check result
