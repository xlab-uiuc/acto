import argparse
import logging
import os

from acto.common import kubernetes_client
from acto.system_state.kubernetes_system_state import KubernetesSystemState


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Collect the system state of a Kubernetes cluster under a namespace"
        " and dump it to a file. Check the health of the system state."
    )
    parser.add_argument(
        "--output",
        required=False,
        default="system_state.json",
        help="Path to dump the system state to",
    )
    parser.add_argument(
        "--kubeconfig",
        required=False,
        default=f"{os.environ['HOME']}/.kube/config",
        help="Path to the kubeconfig file",
    )
    parser.add_argument(
        "--kubecontext",
        required=False,
        default="kind-kind",
        help="Name of the Kubernetes context to use",
    )
    parser.add_argument(
        "--namespace",
        required=False,
        default="default",
        help="Namespace to collect the system state under",
    )
    args = parser.parse_args()

    api_client = kubernetes_client(args.kubeconfig, args.kubecontext)

    system_state = KubernetesSystemState.from_api_client(
        api_client, args.namespace
    )
    system_state.dump(args.output)
    logging.info("System state dumped to %s", args.output)

    health_status = system_state.check_health()
    if health_status.is_healthy() is False:
        logging.error(
            "System state is not healthy with errors: \n%s",
            str(health_status),
        )


if __name__ == "__main__":
    main()
