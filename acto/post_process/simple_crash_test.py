import glob
import json
import logging
import math
import multiprocessing
import os
import queue
import re
import subprocess
import sys
import threading
import time
from functools import partial
from typing import Dict, List

import kubernetes
import kubernetes.client.models as k8s_models

from acto.common import kubernetes_client
from acto.deploy import Deploy
from acto.kubectl_client.kubectl import KubectlClient
from acto.kubernetes_engine import kind
from acto.lib.operator_config import OperatorConfig
from acto.post_process.post_diff_test import DeployRunner, DiffTestResult, PostDiffTest
from acto.post_process.post_process import Step
from acto.runner.runner import Runner
from acto.serialization import ActoEncoder
from acto.utils.error_handler import handle_excepthook, thread_excepthook


def get_crash_config_map(
        apiclient: kubernetes.client.ApiClient,
        trial_dir: str,
        generation: int) -> dict:
    logging.info(
        f"Getting the configmap for the crash test along with system states")
    core_v1_api = kubernetes.client.CoreV1Api(apiclient)
    config_map = core_v1_api.read_namespaced_config_map(
        name="fault-injection-config",
        namespace="default",
    )
    with open(os.path.join(trial_dir, f"crash-config-{generation}.json"), "w") as f:
        json.dump(config_map.to_dict(), f, cls=ActoEncoder, indent=6)
    return config_map.to_dict()


def create_crash_config_map(
        apiclient: kubernetes.client.ApiClient,
        cr_kind: str,
        namespace: str,
        cr_name: str):
    core_v1_api = kubernetes.client.CoreV1Api(apiclient)
    config_map = k8s_models.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=k8s_models.V1ObjectMeta(
            name="fault-injection-config",
        ),
        data={
            "cr_key": f"{cr_kind}/{namespace}/{cr_name}",
            "current": "0",
            "expected": "1",
        },
    )
    core_v1_api.create_namespaced_config_map(
        namespace="default",
        body=config_map,
    )


def replace_crash_config_map(
        apiclient: kubernetes.client.ApiClient,
        cr_kind: str,
        namespace: str,
        cr_name: str,
        operator_log: str):

    # Counting how many requests in total in the step
    count = 0
    for line in operator_log:
        if re.match(r"^Reconciling.*(Create|Update).*", line):
            count += 1

    target_count = math.floor(count * 0.7)
    logging.info(
        f"Setting the target count to {target_count} out of {count} requests")

    core_v1_api = kubernetes.client.CoreV1Api(apiclient)
    config_map = k8s_models.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=k8s_models.V1ObjectMeta(
            name="fault-injection-config",
        ),
        data={
            "cr_key": f"{cr_kind}/{namespace}/{cr_name}",
            "current": "0",
            "expected": str(target_count),
        },
    )
    core_v1_api.replace_namespaced_config_map(
        name="fault-injection-config",
        namespace="default",
        body=config_map,
    )


class CrashTrialRunner(DeployRunner):

    def __init__(
            self,
            workqueue: multiprocessing.Queue,
            context: dict,
            deploy: Deploy,
            workdir: str,
            cluster: kind.Kind,
            worker_id: int,
            acto_namespace: int):
        super().__init__(workqueue, context, deploy,
                         workdir, cluster, worker_id, acto_namespace)

        # Prepare the hook to create the configmap for the fault injection
        cr_kind = self._context["crd"]["body"]["spec"]["names"]["kind"]
        namespace = self._context["namespace"]
        cr_name = "test-cluster"
        self._hook = partial(replace_crash_config_map, cr_kind=cr_kind,
                             namespace=namespace, cr_name=cr_name)

    def run(self):
        while True:
            try:
                trial, steps = self._workqueue.get(block=False)
            except queue.Empty:
                break

            trial_dir = os.path.join(self._workdir, trial)
            os.makedirs(trial_dir, exist_ok=True)
            before_k8s_bootstrap_time = time.time()
            self._cluster.restart_cluster(self._cluster_name, self._kubeconfig)
            self._cluster.load_images(self._images_archive, self._cluster_name)
            apiclient = kubernetes_client(self._kubeconfig, self._context_name)
            kubectl_client = KubectlClient(
                self._kubeconfig, self._context_name)
            after_k8s_bootstrap_time = time.time()
            deployed = self._deploy.deploy_with_retry(
                self._kubeconfig,
                self._context_name,
                kubectl_client=kubectl_client,
                namespace=self._context["namespace"])
            after_operator_deploy_time = time.time()

            runner = Runner(
                self._context, trial_dir, self._kubeconfig, self._context_name,
                custom_system_state_f=get_crash_config_map, operator_container_name=self._deploy.operator_container_name)

            steps: Dict[str, Step]
            for key in sorted(steps, key=lambda x: int(x)):
                step = steps[key]
                logging.info(f"Running trial {trial} gen {step.gen}")
                hook = partial(self._hook, operator_log=step.operator_log)
                snapshot, err = runner.run(step.input, step.gen, [hook])
                after_run_time = time.time()
                difftest_result = DiffTestResult(
                    input_digest=step.input_digest, snapshot=snapshot.to_dict(),
                    originals=[{"trial": trial, "gen": step.gen}],
                    time={"k8s_bootstrap": after_k8s_bootstrap_time -
                          before_k8s_bootstrap_time,
                          "operator_deploy": after_operator_deploy_time -
                          after_k8s_bootstrap_time, "run": after_run_time -
                          after_operator_deploy_time, },)
                difftest_result_path = os.path.join(
                    trial_dir, "difftest-%03d.json" % step.gen)
                difftest_result.to_file(difftest_result_path)


class SimpleCrashTest(PostDiffTest):
    """Crash injection test for the operator using the existing testrun

    This currently is still a prototype, where it depends on the operators' cooperation
    to inject the crash. The operator needs to implement a configmap that can be used
    to inject the crash. The configmap should have the following format:
    {
        "cr_key": "<cr_kind>/<cr_namespace>/<cr_name>",
        "current": "<current_count>",
        "expected": "<expected_count>",
    }
    The operator should also implement a hook to update the configmap when the
    operator is running. The hook should be called after the operator has processed
    a certain number of requests. The hook should update the "current" field of the
    configmap to the number of requests that the operator has processed. The hook
    should also update the "expected" field of the configmap to the number of requests
    that the operator is expected to process.
    """

    def __init__(
            self,
            testrun_dir: str,
            config: OperatorConfig,
            ignore_invalid: bool = False,
            acto_namespace: int = 0):
        super().__init__(testrun_dir, config, ignore_invalid, acto_namespace)

        compare_results_files = glob.glob(os.path.join(
            testrun_dir, "post_diff_test", "compare-results-*.json"))
        for compare_results_file in compare_results_files:
            digest = re.search(r"compare-results-(\w+).json",
                               compare_results_file).group(1)
            del self.unique_inputs[digest]

        logging.info(
            f"Running Unique inputs excluding errorneous ones: {len(self.unique_inputs)}")

    def post_process(self, workdir: str, num_workers: int = 1):
        if not os.path.exists(workdir):
            os.mkdir(workdir)

        # Prepare the hook to create the configmap for the fault injection
        cr_kind = self._context["crd"]["body"]["spec"]["names"]["kind"]
        namespace = self._context["namespace"]
        cr_name = "test-cluster"
        posthook = partial(create_crash_config_map, cr_kind=cr_kind,
                           namespace=namespace, cr_name=cr_name)

        cluster = kind.Kind(
            acto_namespace=self.acto_namespace,
            posthooks=[posthook],
            feature_gates=self.config.kubernetes_engine.feature_gates)
        cluster.configure_cluster(
            self.config.num_nodes, self.config.kubernetes_version)
        deploy = Deploy(self.config.deploy)

        # Build an archive to be preloaded
        images_archive = os.path.join(workdir, "images.tar")
        if len(self.context["preload_images"]) > 0:
            # first make sure images are present locally
            for image in self.context["preload_images"]:
                subprocess.run(["docker", "pull", image])
            subprocess.run(["docker", "image", "save", "-o", images_archive] +
                           list(self.context["preload_images"]))

        ################## Operation sequence crash test ######################
        num_ops = 0
        workqueue = multiprocessing.Queue()
        for trial, steps in self._trial_to_steps.items():
            new_steps = {}
            for step_key in list(steps.keys()):
                if not steps[step_key].runtime_result.is_error():
                    new_steps[step_key] = steps[step_key]
                    num_ops += 1
            workqueue.put((trial, new_steps))
        logging.info(f"Running {num_ops} trials")

        runners: List[CrashTrialRunner] = []
        for i in range(num_workers):
            runner = CrashTrialRunner(workqueue, self.context, deploy,
                                      workdir, cluster, i, self.acto_namespace)
            runners.append(runner)

        processes = []
        for runner in runners:
            p = multiprocessing.Process(target=runner.run)
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        ################### Single operation crash test #######################
        workqueue = multiprocessing.Queue()
        for unique_input_group in self.unique_inputs.values():
            workqueue.put(unique_input_group)

        runners: List[DeployRunner] = []
        for i in range(num_workers):
            runner = DeployRunner(workqueue, self.context, deploy,
                                  workdir, cluster, i, self.acto_namespace)
            runners.append(runner)

        processes = []
        for runner in runners:
            p = multiprocessing.Process(target=runner.run)
            p.start()
            processes.append(p)

        for p in processes:
            p.join()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--testrun-dir", type=str, required=True)
    parser.add_argument("--workdir-path", type=str, required=True)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--checkonly", action="store_true")
    args = parser.parse_args()

    # Register custom exception hook
    sys.excepthook = handle_excepthook
    threading.excepthook = thread_excepthook
    global notify_crash_
    notify_crash_ = True

    log_filename = "check.log" if args.checkonly else "test.log"
    os.makedirs(args.workdir_path, exist_ok=True)
    # Setting up log infra
    logging.basicConfig(
        filename=os.path.join(args.workdir_path, log_filename),
        level=logging.DEBUG, filemode="w",
        format="%(asctime)s %(levelname)-7s, %(name)s, %(filename)-9s:%(lineno)d, %(message)s")
    logging.getLogger("kubernetes").setLevel(logging.ERROR)
    logging.getLogger("sh").setLevel(logging.ERROR)

    start = time.time()

    with open(args.config, "r") as config_file:
        config = OperatorConfig(**json.load(config_file))
    p = SimpleCrashTest(testrun_dir=args.testrun_dir, config=config)
    if not args.checkonly:
        p.post_process(args.workdir_path, num_workers=args.num_workers)
    p.check(args.workdir_path, num_workers=args.num_workers)

    logging.info(f"Total time: {time.time() - start} seconds")
