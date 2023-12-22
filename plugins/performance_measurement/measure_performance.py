import argparse
import dataclasses
import glob
import json
import logging
import os
import threading
from datetime import datetime
from functools import partial
from typing import Callable

import kubernetes
import yaml
from fluent_inputs import FluentInputGenerator
from measure_runner import MeasurementRunner
from performance_measurement.cadvisor_watcher import CAdvisorWatcher
from performance_measurement.metrics_api_watcher import MetricsApiWatcher
from rabbitmq_inputs import RabbitMQInputGenerator
from zk_inputs import ZooKeeperInputGenerator

from acto import utils
from acto.common import kubernetes_client
from acto.constant import CONST
from acto.deploy import Deploy
from acto.kubectl_client.kubectl import KubectlClient
from acto.kubernetes_engine import kind
from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_chain_inputs import ChainInputs
from acto.utils.preprocess import process_crd


def load_inputs_from_dir(dir: str) -> list:
    inputs = []
    files = sorted(glob.glob(f"{dir}/input-*.yaml"))
    logging.info(f"Loading {len(files)} inputs from {dir}")
    for file in files:
        with open(file, "r") as f:
            inputs.append(yaml.load(f, Loader=yaml.FullLoader))
    return inputs


def deploy_metrics_server(
    apiclient: kubernetes.client.ApiClient, kubectl_client: KubectlClient
):
    """Deploy metrics server"""
    logging.info("Deploying metrics server")
    p = kubectl_client.kubectl(["apply", "-f", "data/metrics-server.yaml"])
    if p.returncode != 0:
        logging.error("Failed to deploy metrics server")
        return False


def test_normal(
    workdir: str,
    input_dir: str,
    config: OperatorConfig,
    sts_name_f: Callable[[dict], str],
    ds_name_f: Callable[[dict], str],
    modes: list,
):
    # prepare workloads
    workloads = load_inputs_from_dir(dir=input_dir)

    configuration = kubernetes.client.Configuration()
    configuration.verify_ssl = False
    configuration.debug = False
    kubernetes.client.Configuration.set_default(configuration)

    # start the k8s cluster
    kubeconfig = os.path.join(os.path.expanduser("~"), ".kube", "anvil")
    deploy_metrics_server_f = partial(
        deploy_metrics_server,
        kubectl_client=KubectlClient(kubeconfig, "kind-anvil"),
    )
    cluster = kind.Kind(
        acto_namespace=0,
        posthooks=[deploy_metrics_server_f],
        feature_gates=config.kubernetes_engine.feature_gates,
    )
    cluster.configure_cluster(config.num_nodes, config.kubernetes_version)
    cluster.restart_cluster(name="anvil", kubeconfig=kubeconfig)

    # deploy the operator
    context_name = cluster.get_context_name(f"anvil")
    deploy = Deploy(config.deploy)
    namespace = (
        utils.get_yaml_existing_namespace(deploy.operator_yaml)
        or CONST.ACTO_NAMESPACE
    )
    kubectl_client = KubectlClient(kubeconfig, context_name)
    deployed = deploy.deploy_with_retry(
        kubeconfig, context_name, kubectl_client, namespace
    )
    if not deployed:
        logging.info("Not deployed. Try again!")

    # run the workload
    crd = process_crd(
        kubernetes_client(kubeconfig, context_name),
        KubectlClient(kubeconfig, context_name),
        config.crd_name,
    )

    if "normal" in modes:
        # operation sequence
        trial_dir = f"{workdir}/trial-normal"
        os.makedirs(trial_dir, exist_ok=True)

        runner = MeasurementRunner(
            namespace, crd, trial_dir, kubeconfig, context_name
        )

        # start the stats watcher
        control_plane_stats_dir = os.path.join(trial_dir, "control_plane_stats")
        os.makedirs(control_plane_stats_dir, exist_ok=True)
        cadvisor_watcher = CAdvisorWatcher(control_plane_stats_dir)
        pods_watcher = MetricsApiWatcher(control_plane_stats_dir)
        watcher_thread = threading.Thread(
            target=cadvisor_watcher.start,
            args=(kubernetes_client(kubeconfig, context_name),),
        )
        pods_watcher_thread = threading.Thread(
            target=pods_watcher.start,
            args=(
                kubernetes_client(kubeconfig, context_name),
                deploy.operator_name(),
            ),
        )
        watcher_thread.start()
        pods_watcher_thread.start()

        # run the workload
        gen = 0
        for workload in workloads:
            measurement_result = runner.run(
                workload, sts_name_f, ds_name_f, gen
            )
            if measurement_result is not None:
                measurement_result_file = (
                    f"{trial_dir}/measurement_result_{gen:03d}.json"
                )
                with open(measurement_result_file, "w") as f:
                    json.dump(dataclasses.asdict(measurement_result), f)
            gen += 1

        # stop the stats watchers
        cadvisor_watcher.stop()
        pods_watcher.stop()
        watcher_thread.join()
        pods_watcher_thread.join()

    if "single-operation" in modes:
        # single operation
        # prepare workloads
        workloads = load_inputs_from_dir(dir=input_dir)

        single_operation_trial_dir = f"{workdir}/trial-single-operation"
        os.makedirs(single_operation_trial_dir, exist_ok=True)
        control_plane_stats_dir = os.path.join(
            single_operation_trial_dir, "control_plane_stats"
        )
        os.makedirs(control_plane_stats_dir, exist_ok=True)

        cadvisor_watcher = CAdvisorWatcher(control_plane_stats_dir)
        pods_watcher = MetricsApiWatcher(control_plane_stats_dir)

        gen = 0
        for workload in workloads:
            cluster.restart_cluster(name="anvil", kubeconfig=kubeconfig)
            runner = MeasurementRunner(
                namespace,
                crd,
                single_operation_trial_dir,
                kubeconfig,
                context_name,
            )
            kubectl_client = KubectlClient(kubeconfig, context_name)
            deployed = deploy.deploy_with_retry(
                kubeconfig, context_name, kubectl_client, namespace
            )
            if not deployed:
                logging.info("Not deployed. Try again!")

            watcher_thread = threading.Thread(
                target=cadvisor_watcher.start,
                args=(kubernetes_client(kubeconfig, context_name),),
            )
            pods_watcher_thread = threading.Thread(
                target=pods_watcher.start,
                args=(
                    kubernetes_client(kubeconfig, context_name),
                    deploy.operator_name(),
                ),
            )
            watcher_thread.start()
            pods_watcher_thread.start()

            measurement_result = runner.run(
                workload, sts_name_f, ds_name_f, gen
            )
            if measurement_result is not None:
                measurement_result_file = f"{single_operation_trial_dir}/measurement_result_{gen:03d}.json"
                with open(measurement_result_file, "w") as f:
                    json.dump(dataclasses.asdict(measurement_result), f)
            gen += 1

            # stop the stats watchers
            cadvisor_watcher.stop()
            pods_watcher.stop()
            watcher_thread.join()
            pods_watcher_thread.join()


def generate_inputs(
    testrun_dir: str, input_generator: ChainInputs, config: OperatorConfig
):
    chain_inputs = input_generator(testrun_dir=testrun_dir, config=config)
    os.makedirs(f"{testrun_dir}/inputs", exist_ok=True)
    chain_inputs.serialize(f"{testrun_dir}/inputs")


def main(args):
    input_generator: ChainInputs = None
    sts_name_f = None
    if args.project == "rabbitmq-operator":
        input_generator = RabbitMQInputGenerator
        sts_name_f = MeasurementRunner.rabbitmq_sts_name
        daemonset_name_f = None
    elif args.project == "zookeeper-operator":
        input_generator = ZooKeeperInputGenerator
        sts_name_f = MeasurementRunner.zk_sts_name
        daemonset_name_f = None
    elif args.project == "fluent-operator":
        input_generator = FluentInputGenerator
        sts_name_f = None
        daemonset_name_f = MeasurementRunner.fluent_ds_name

    # parse the inputs
    with open(args.anvil_config, "r") as config_file:
        config = json.load(config_file)
        if "monkey_patch" in config:
            del config["monkey_patch"]
        config = OperatorConfig(**config)

    if args.gen:
        generate_inputs(args.input_dir, input_generator, config)
        return

    # Run the Anvil performance test
    if "anvil" in args.phase:
        anvil_workdir = f"{args.workdir_path}/anvil"
        os.makedirs(anvil_workdir, exist_ok=True)
        test_normal(
            anvil_workdir,
            f"{args.input_dir}/inputs/anvil_inputs",
            config,
            sts_name_f,
            daemonset_name_f,
            modes=args.modes,
        )

    # Run the reference performance test
    # reference_config = "data/zookeeper-operator/v0.2.15/config.json"
    if "reference" in args.phase:
        with open(args.reference_config, "r") as config_file:
            config = json.load(config_file)
            if "monkey_patch" in config:
                del config["monkey_patch"]
            config = OperatorConfig(**config)

        reference_dir = f"{args.workdir_path}/reference"
        test_normal(
            reference_dir,
            f"{args.input_dir}/inputs/reference",
            config,
            sts_name_f,
            daemonset_name_f,
            modes=args.modes,
        )


if __name__ == "__main__":
    workdir_path = "testrun-%s" % datetime.now().strftime("%Y-%m-%d-%H-%M")

    parser = argparse.ArgumentParser(
        description="Collecting Performance for k8s/openshift Operators Workload"
    )
    parser.add_argument(
        "--workdir",
        dest="workdir_path",
        type=str,
        default=workdir_path,
        help="Working directory",
    )
    parser.add_argument(
        "--input-dir",
        dest="input_dir",
        required=True,
        help="The directory of the trial folder to reproduce. CR files should have names starting with 'mutated-'",
    )
    parser.add_argument(
        "--anvil-config",
        "-c",
        dest="anvil_config",
        help="Anvil operator port config path",
    )
    parser.add_argument(
        "--reference-config",
        "-r",
        dest="reference_config",
        help="Reference operator port config path",
    )
    parser.add_argument(
        "--phase",
        "-p",
        dest="phase",
        nargs="+",
        default=["anvil", "reference"],
        help="The phase of the trial to reproduce",
    )
    parser.add_argument(
        "--modes",
        "-m",
        dest="modes",
        nargs="+",
        default=["normal", "single-operation"],
    )
    parser.add_argument(
        "--project",
        "-j",
        dest="project",
        help="The project name to use for the trial",
        required=True,
    )
    parser.add_argument(
        "--gen", "-g", dest="gen", action="store_true", help="Generate inputs"
    )
    args = parser.parse_args()

    os.makedirs(args.workdir_path, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.workdir_path, "performance_measurement.log"),
        level=logging.DEBUG,
        filemode="w",
        format="%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s",
    )
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    main(args)
