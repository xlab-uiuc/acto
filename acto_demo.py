import time
import argparse
import os
import sys
from datetime import datetime
import logging
import signal
import random
from common import get_thread_logger

from deploy import Deploy, DeployMethod
from acto import handle_excepthook, Acto, timeout_handler
from exception import UnknownDeployMethodError

random.seed(0)

if __name__ == '__main__':
    start_time = time.time()
    workdir_path = 'testrun-%s' % datetime.now().strftime('%Y-%m-%d-%H-%M')

    parser = argparse.ArgumentParser(
        description='Automatic, Continuous Testing for k8s/openshift Operators')
    parser.add_argument('--seed',
                        '-s',
                        dest='seed',
                        required=True,
                        help="seed CR file")
    deploy_method = parser.add_mutually_exclusive_group(required=True)
    deploy_method.add_argument('--operator',
                               '-o',
                               dest='operator',
                               required=False,
                               help="yaml file for deploying the\
                                operator with kubectl")
    deploy_method.add_argument('--helm',
                               dest='operator_chart',
                               required=False,
                               help='Path of operator helm chart')
    deploy_method.add_argument('--kustomize',
                               dest='kustomize',
                               required=False,
                               help='Path of folder with kustomize')
    parser.add_argument('--init',
                        dest='init',
                        required=False,
                        help='Path of init yaml file (deploy before operator)')
    parser.add_argument('--duration',
                        '-d',
                        dest='duration',
                        required=False,
                        help='Number of hours to run')
    parser.add_argument('--preload-images',
                        dest='preload_images',
                        nargs='*',
                        help='Docker images to preload into Kind cluster')
    parser.add_argument(
        '--crd-name',
        dest='crd_name',
        help='Name of CRD to use, required if there are multiple CRDs')
    # Temporary solution before integrating controller-gen
    parser.add_argument(
        '--helper-crd',
        dest='helper_crd',
        help='generated CRD file that helps with the input generation')
    parser.add_argument(
        '--custom-fields',
        dest='custom_fields',
        help='Python source file containing a list of custom fields')
    parser.add_argument('--context', dest='context', help='Cached context data')
    parser.add_argument('--dryrun',
                        dest='dryrun',
                        action='store_true',
                        help='Only generate test cases without executing them')

    args = parser.parse_args()

    os.makedirs(workdir_path, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(workdir_path, 'test.log'),
        level=logging.DEBUG,
        filemode='w',
        format=
        '%(asctime)s %(levelname)-6s, %(name)s, %(filename)s:%(lineno)d, %(message)s'
    )
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    # Register custom exception hook
    sys.excepthook = handle_excepthook

    # We don't need this now, but it would be nice to support this in the future
    # candidate_dict = construct_candidate_from_yaml(args.candidates)
    # logging.debug(candidate_dict)
    logger = get_thread_logger(with_prefix=False)

    logger.info('Acto started with [%s]' % sys.argv)

    # Preload frequently used images to amid ImagePullBackOff
    if args.preload_images:
        logger.info('%s will be preloaded into Kind cluster',
                     args.preload_images)

    # register timeout to automatically stop after # hours
    if args.duration != None:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(args.duration) * 60 * 60)
    if args.operator_chart:
        deploy = Deploy(DeployMethod.HELM, args.operator_chart, args.init).new()
    elif args.operator:
        deploy = Deploy(DeployMethod.YAML, args.operator, args.init).new()
    elif args.kustomize:
        deploy = Deploy(DeployMethod.KUSTOMIZE, args.kustomize, args.init).new()
    else:
        raise UnknownDeployMethodError()

    if args.context == None:
        context_cache = os.path.join(os.path.dirname(args.seed), 'context.json')
    else:
        context_cache = args.context

    acto = Acto(args.seed, deploy, workdir_path, args.crd_name, args.preload_images,
                args.custom_fields, args.helper_crd, context_cache, args.dryrun, mount=['spec', 'persistence'])
    acto.run()