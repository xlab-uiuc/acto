import argparse
from functools import partial
import json
import subprocess
import jsonpatch
from testplan import TreeNode

from value_with_schema import ValueWithSchema
from test_case import TestCase
from common import get_thread_logger
import acto

def apply_testcase(value_with_schema: ValueWithSchema,
                   path: list,
                   testcase: TestCase,
                   setup: bool = False) -> jsonpatch.JsonPatch:
    logger = get_thread_logger(with_prefix=True)
    next_cr = testcase.mutator(None)  # next cr in yaml format

    value_with_schema.update(next_cr)

    patch = jsonpatch.make_patch(prev, curr)
    logger.info('JSON patch: %s' % patch)
    return patch

class ReproInputModel:
    def __init__(self, cr_list: list) -> None:
        self.mount = ['spec']
        self.testcases = []
        for cr in cr_list:
            cr_mutator = partial(repro_mutator, cr)
            t = TestCase(repro_precondition, cr_mutator, repro_setup)
            self.testcases.append(t)
    
    def next_test(self) -> list:
        return [TreeNode(), self.testcases.pop(0)] # return the first test case

    ## Some other methods of InputModel

class ReproActo(acto.Acto):
    def __init__()
    pass

def repro_precondition(v):
    return True

def repro_mutator(cr, v):
    return cr

def repro_setup(v):
    return None

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
