import argparse
from distutils.log import error
import os
import kubernetes
import yaml
import time

def construct_kind_cluster():
    '''Delete kind cluster then create a new one
    '''
    os.system('kind delete cluster')
    os.system('kind create cluster')

def deploy_operator(operator_yaml_path: str):
    '''Deploy operator according to yaml
    @param operator_yaml_path - path pointing to the operator yaml file
    '''
    with open(operator_yaml_path, 'r') as operator_yaml:
        parsed_operator_yaml = yaml.load(operator_yaml, Loader=yaml.FullLoader)
        parsed_operator_yaml['metadata']['labels'].append('testing/tag=testing')
        os.system('kubectl apply -f %s' % operator_file)
    
        kubernetes.config.load_kube_config()
        corev1 = kubernetes.client.CoreV1Api()

        print('Deploying the operator, waiting for it to be ready')
        pod_ready = False
        for _ in range(600):
            project_pod = corev1.list_namespaced_pod(
                parsed_operator_yaml['metadata']['namespace'],
                watch=False,
                label_selector='testing/tag=testing'
            )
            if len(project_pod) >= 1 and project_pod[0].status.phase == 'Running':
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
    #     time.sleep(1)
    #     # TODO: test input generation

    #     # TODO: submit to operator

    #     # TODO: check result