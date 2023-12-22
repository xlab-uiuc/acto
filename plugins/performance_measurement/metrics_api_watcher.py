"""This module contains the MetricsApiWatcher class"""

import json
import logging
import os
import time
from typing import List

import kubernetes
from kubernetes.client import ApiClient


class MetricsApiWatcher:
    """This class is used to watch the metrics api of the control plane pod."""

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
            os.path.join(self._output_dir, f"pods_stats.{sequence:08d}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(stats_buf, f, indent=4)

    def start(self, apiclient: ApiClient, operator_name: str):
        """Start watching the metrics api of the control plane pod"""
        stats_buf: List[dict] = []
        custom_api = kubernetes.client.CustomObjectsApi(apiclient)

        while True:
            if self._stop:
                break
            stats = custom_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods",
            )
            pod_metrics = {}
            for pod in stats["items"]:
                pod_name = pod["metadata"]["name"]
                if pod_name == "etcd-anvil-control-plane":
                    pod_metrics[pod_name] = pod
                elif operator_name in pod_name:
                    pod_metrics[pod_name] = pod

            if pod_metrics:
                stats_buf.append(pod_metrics)
            if len(stats_buf) >= 100:
                self.write_stats(stats_buf, self._sequence)
                stats_buf = []
                self._sequence += 1
            time.sleep(1)
        if len(stats_buf) > 0:
            logging.info(
                "Stopped, Writing %d stats to file",
                len(stats_buf),
            )
            self.write_stats(stats_buf, self._sequence)
            self._sequence += 1
        return

    def stop(self):
        """Stop watching the metrics api of the control plane pod"""
        self._stop = True
