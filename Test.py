import argparse
from distutils.log import error
import os
import kubernetes
import yaml
import time


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
    with open(operator_yaml_path,
              'r') as operator_yaml, open('new_operator.yaml', 'w') as out_yaml:
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
        for _ in range(600):
            operator_deployments = appv1.list_namespaced_deployment(
                namespace, watch=False,
                label_selector='testing/tag=testing').items
            if len(operator_deployments
                  ) >= 1 and get_deployment_available_status(
                      operator_deployments[0]):
                print('Operator ready')
                pod_ready = True
                break
            time.sleep(1)
        if not pod_ready:
            error("waiting for the operator pod to be ready")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Continuous testing')

    construct_kind_cluster()
    deploy_operator('cluster-operator.yml')

    # while True:
    #     # TODO: test input generation
    #     # TODO: submit to operator
    #     # TODO: check result
