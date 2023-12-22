import json
import logging
import os
from typing import List

from acto.kubernetes_engine.base import KubernetesEngine


class WatchStats:
    def __init__(self, cluster_name: str, output_dir: str) -> None:
        self._cluster_name = cluster_name
        self._output_dir = output_dir
        self._sequence = 0
        self._stop = False

    def write_stats(self, stats_buf: List[dict], sequence: int):
        with open(
            os.path.join(
                self._output_dir,
                f"{self._cluster_name}_stats.{sequence:08d}.json",
            ),
            "w",
        ) as f:
            json.dump(stats_buf, f, indent=4)

    def start(self, cluster: KubernetesEngine):
        stats_buf = []
        stats_stream = cluster.stream_control_plane_stats("anvil")
        for stats in stats_stream:
            if self._stop:
                break
            stats_buf.append(stats)
            if len(stats_buf) >= 100:
                self.write_stats(stats_buf, self._sequence)
                stats_buf = []
                self._sequence += 1
        if len(stats_buf) > 0:
            logging.info(f"Stopped, Writing {len(stats_buf)} stats to file")
            self.write_stats(stats_buf, self._sequence)
            self._sequence += 1
        return

    def stop(self):
        self._stop = True
