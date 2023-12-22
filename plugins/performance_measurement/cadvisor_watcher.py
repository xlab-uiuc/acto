import json
import logging
import os
import time
from collections import defaultdict
from typing import List

import kubernetes
from kubernetes.client import ApiClient
from prometheus_client.parser import text_string_to_metric_families


class CAdvisorWatcher:
    def __init__(self, output_dir: str) -> None:
        """Initialize the WatchPodStats class

        Args:
            apiclient: kubernetes client
            operator_name: name of the operator
            output_dir: output directory
        """
        self._output_dir = output_dir
        self._sequence = 0
        self._stop = False

    def write_stats(self, stats_buf: List[dict], sequence: int):
        with open(
            os.path.join(
                self._output_dir, f"cadvisor_stats.{sequence:08d}.json"
            ),
            "w",
        ) as f:
            json.dump(stats_buf, f, indent=4)

    def start(self, apiclient: ApiClient):
        stats_buf: List[dict] = []
        corev1 = kubernetes.client.CoreV1Api(apiclient)

        while True:
            if self._stop:
                break
            stats = corev1.connect_get_node_proxy_with_path(
                name="anvil-control-plane", path="/metrics/cadvisor"
            )

            pod_metrics = defaultdict(dict)
            for family in text_string_to_metric_families(stats):
                for sample in family.samples:
                    name = sample.name
                    labels = sample.labels
                    value = sample.value
                    timestamp = sample.timestamp

                    if name == "container_fs_writes_bytes_total":
                        if labels["container"] == "etcd":
                            pod_metrics["etcd-anvil-control-plane"][
                                "container_fs_writes_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}
                        elif labels["container"] == "kube-apiserver":
                            pod_metrics["kube-apiserver"][
                                "container_fs_writes_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}
                    elif name == "container_fs_reads_bytes_total":
                        if labels["container"] == "etcd":
                            pod_metrics["etcd-anvil-control-plane"][
                                "container_fs_reads_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}
                        elif labels["container"] == "kube-apiserver":
                            pod_metrics["kube-apiserver"][
                                "container_fs_reads_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}
                    elif name == "container_cpu_usage_seconds_total":
                        if labels["container"] == "etcd":
                            pod_metrics["etcd-anvil-control-plane"][
                                "container_cpu_usage_seconds_total"
                            ] = {"value": value, "timestamp": timestamp}
                        elif labels["container"] == "kube-apiserver":
                            pod_metrics["kube-apiserver"][
                                "container_cpu_usage_seconds_total"
                            ] = {"value": value, "timestamp": timestamp}
                    elif name == "container_memory_usage_bytes":
                        if labels["container"] == "etcd":
                            pod_metrics["etcd-anvil-control-plane"][
                                "container_memory_usage_bytes"
                            ] = {"value": value, "timestamp": timestamp}
                        elif labels["container"] == "kube-apiserver":
                            pod_metrics["kube-apiserver"][
                                "container_memory_usage_bytes"
                            ] = {"value": value, "timestamp": timestamp}
                    elif name == "container_network_transmit_bytes_total":
                        if labels["pod"] == "etcd-anvil-control-plane":
                            pod_metrics["etcd-anvil-control-plane"][
                                "container_network_transmit_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}
                        elif (
                            labels["pod"]
                            == "kube-apiserver-anvil-control-plane"
                        ):
                            pod_metrics["kube-apiserver"][
                                "container_network_transmit_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}
                    elif name == "container_network_receive_bytes_total":
                        if labels["pod"] == "etcd-anvil-control-plane":
                            pod_metrics["etcd-anvil-control-plane"][
                                "container_network_receive_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}
                        elif (
                            labels["container"]
                            == "kube-apiserver-anvil-control-plane"
                        ):
                            pod_metrics["kube-apiserver"][
                                "container_network_receive_bytes_total"
                            ] = {"value": value, "timestamp": timestamp}

            if pod_metrics:
                stats_buf.append(pod_metrics)
            if len(stats_buf) >= 100:
                self.write_stats(stats_buf, self._sequence)
                stats_buf = []
                self._sequence += 1
            time.sleep(1)
        if len(stats_buf) > 0:
            logging.info(f"Stopped, Writing {len(stats_buf)} stats to file")
            self.write_stats(stats_buf, self._sequence)
            self._sequence += 1
        return

    def stop(self):
        self._stop = True
