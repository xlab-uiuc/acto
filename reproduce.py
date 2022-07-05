import argparse
import json
import subprocess

from acto import construct_kind_cluster
from constant import CONST
from deploy import Deploy, DeployMethod
from exception import UnknownDeployMethodError
from common import kind_load_images, kubectl

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Deploys operator with the seed CR')
    parser.add_argument('--seed',
                        '-s',
                        dest='seed',
                        required=True,
                        help="seed CR file")
    parser.add_argument('--operator',
                        '-o',
                        dest='operator',
                        required=False,
                        help="yaml file for deploying the operator")
    parser.add_argument('--helm',
                        dest='operator_chart',
                        required=False,
                        help='Path of operator helm chart')
    parser.add_argument('--kustomize',
                        dest='kustomize',
                        required=False,
                        help='Path of folder with kustomize')
    parser.add_argument('--init',
                        dest='init',
                        required=False,
                        help='Path of init yaml file (deploy before operator)')
    parser.add_argument('--context', dest='context', help='Cached context data')

    args = parser.parse_args()

    if args.operator_chart:
        deploy = Deploy(DeployMethod.HELM, args.operator_chart, args.init).new()
    elif args.operator:
        deploy = Deploy(DeployMethod.YAML, args.operator, args.init).new()
    elif args.kustomize:
        deploy = Deploy(DeployMethod.KUSTOMIZE, args.kustomize, args.init).new()
    else:
        raise UnknownDeployMethodError()

    construct_kind_cluster('test', CONST.K8S_VERSION)
    with open(args.context, 'r') as context_fin:
        context = json.load(context_fin)
        context['preload_images'] = set(context['preload_images'])
    # kind_load_images(context['preload_images'], 'test') # FIXME the first parameter is not a str, while it is expected to be
    deployed = deploy.deploy_with_retry(context, 'test')

    cmd = ['kubectl', 'apply', '-f', args.seed, '-n', context['namespace']]
    subprocess.run(cmd)
    kubectl(['apply', '-f', args.seed, '-n', context['namespace']], 'test')
