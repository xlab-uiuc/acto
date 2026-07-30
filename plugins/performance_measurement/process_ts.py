"""Process the time series data collected from the experiment."""

import csv
import datetime
import glob
import json
import os
from typing import List, Optional, Tuple

import kubernetes
import numpy as np
import pandas as pd
import tabulate
from matplotlib import pyplot as plt

ineffective_files = set()

# Rows for the reconcile/end-to-end LaTeX table (welder-table-2.txt). Each
# entry is {"name": controller_name, "reconcile": (verified, ref, diff_mean,
# diff_std), "e2e": (verified, ref, diff_mean, diff_std)}.
controller_table_rows = []


def geometric_mean(series: pd.Series) -> float:
    return np.exp(np.log(series).mean())


def _paired_stats(
    df: pd.DataFrame, verified_col: str, ref_col: str
) -> Tuple[float, float, float, float]:
    """Return (verified_mean, ref_mean, diff_mean, diff_std) for a pair of
    per-trial duration columns, restricted to trials where both are present."""
    valid = df[[verified_col, ref_col]].dropna()
    diff = valid[verified_col] - valid[ref_col]
    return (
        valid[verified_col].mean(),
        valid[ref_col].mean(),
        diff.mean(),
        diff.std(),
    )


def process_ts(files: List[str]) -> pd.DataFrame:
    condition_durations = []
    has_condition_3 = False
    has_condition_4 = False
    has_condition_5 = False
    for ts_datafile in sorted(files):
        with open(ts_datafile, "r") as f:
            data = json.load(f)

            if data["condition_2_ts"] < 0:
                continue
            condition_2_duration = data["condition_2_ts"] - data["start_ts"]
            if condition_2_duration < 1:
                continue
            if condition_2_duration < data["condition_1_ts"] - data["start_ts"]:
                # print(os.path.basename(ts_datafile))
                continue
            # if data['condition_1_ts'] - data['start_ts'] > 1:
            #     print(os.path.basename(ts_datafile))
            #     continue
            row = {
                "name": os.path.basename(ts_datafile),
                "condition_1_duration": data["condition_1_ts"]
                - data["start_ts"],
                "condition_2_duration": condition_2_duration,
            }
            condition_3_ts = data.get("condition_3_ts")
            if condition_3_ts is not None:
                has_condition_3 = True
                row["intermediate_duration_a"] = (
                    condition_3_ts - data["condition_1_ts"]
                )
                row["intermediate_duration_b"] = (
                    data["condition_2_ts"] - data["condition_1_ts"]
                )
            condition_4_ts = data.get("condition_4_ts")
            if condition_4_ts is not None:
                has_condition_4 = True
                row["intermediate_duration_c"] = (
                    condition_4_ts - data["condition_1_ts"]
                )
            condition_5_ts = data.get("condition_5_ts")
            if condition_5_ts is not None:
                has_condition_5 = True
                row["intermediate_duration_e"] = (
                    condition_5_ts - data["start_ts"]
                )
            condition_durations.append(row)

    columns = ["name", "condition_1_duration", "condition_2_duration"]
    if has_condition_3:
        columns += ["intermediate_duration_a", "intermediate_duration_b"]
    if has_condition_4:
        columns += ["intermediate_duration_c"]
    if has_condition_5:
        columns += ["intermediate_duration_e"]

    return pd.DataFrame(
        condition_durations,
        columns=columns,
        index=[x["name"] for x in condition_durations],
    )


def process_cadvisor(
    files: List[str],
) -> Tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame
]:
    etcd_cpu_usages = []
    etcd_memory_usages = []
    etcd_blkio_usages = []
    etcd_blkio_read_usages = []
    etcd_network_read_usages = []
    etcd_network_write_usages = []
    apiserver_cpu_usages = []
    apiserver_memory_usages = []
    start_time = None
    for cadvisor_datafile in sorted(files):
        with open(cadvisor_datafile, "r") as f:
            stats = json.load(f)

            for stat in stats:
                for container_name, container_stat in stat.items():
                    if container_name == "etcd-anvil-control-plane":
                        if start_time is None:
                            start_time = container_stat[
                                "container_cpu_usage_seconds_total"
                            ]["timestamp"]
                        ts = (
                            container_stat["container_cpu_usage_seconds_total"][
                                "timestamp"
                            ]
                            - start_time
                        )
                        if ts >= 0:
                            etcd_cpu_usages.append(
                                {
                                    "timestamp": ts,
                                    "cpu_usage": container_stat[
                                        "container_cpu_usage_seconds_total"
                                    ]["value"],
                                }
                            )
                        ts = (
                            container_stat["container_memory_usage_bytes"][
                                "timestamp"
                            ]
                            - start_time
                        )
                        if ts >= 0:
                            etcd_memory_usages.append(
                                {
                                    "timestamp": ts,
                                    "memory_usage": container_stat[
                                        "container_memory_usage_bytes"
                                    ]["value"],
                                }
                            )
                        ts = (
                            container_stat["container_fs_writes_bytes_total"][
                                "timestamp"
                            ]
                            - start_time
                        )
                        if ts >= 0:
                            etcd_blkio_usages.append(
                                {
                                    "timestamp": ts,
                                    "blkio_write": container_stat[
                                        "container_fs_writes_bytes_total"
                                    ]["value"],
                                }
                            )
                        ts = (
                            container_stat["container_fs_reads_bytes_total"][
                                "timestamp"
                            ]
                            - start_time
                        )
                        if ts >= 0:
                            etcd_blkio_read_usages.append(
                                {
                                    "timestamp": ts,
                                    "blkio_read": container_stat[
                                        "container_fs_reads_bytes_total"
                                    ]["value"],
                                }
                            )
                        ts = (
                            container_stat[
                                "container_network_receive_bytes_total"
                            ]["timestamp"]
                            - start_time
                        )
                        if ts >= 0:
                            etcd_network_read_usages.append(
                                {
                                    "timestamp": ts,
                                    "network_read": container_stat[
                                        "container_network_receive_bytes_total"
                                    ]["value"],
                                }
                            )
                        ts = (
                            container_stat[
                                "container_network_transmit_bytes_total"
                            ]["timestamp"]
                            - start_time
                        )
                        if ts >= 0:
                            etcd_network_write_usages.append(
                                {
                                    "timestamp": ts,
                                    "network_write": container_stat[
                                        "container_network_transmit_bytes_total"
                                    ]["value"],
                                }
                            )
                    elif container_name == "kube-apiserver":
                        if start_time is not None:
                            ts = (
                                container_stat[
                                    "container_cpu_usage_seconds_total"
                                ]["timestamp"]
                                - start_time
                            )
                            if ts >= 0:
                                apiserver_cpu_usages.append(
                                    {
                                        "timestamp": ts,
                                        "cpu_usage": container_stat[
                                            "container_cpu_usage_seconds_total"
                                        ]["value"],
                                    }
                                )
                            ts = (
                                container_stat["container_memory_usage_bytes"][
                                    "timestamp"
                                ]
                                - start_time
                            )
                            if ts >= 0:
                                apiserver_memory_usages.append(
                                    {
                                        "timestamp": ts,
                                        "memory_usage": container_stat[
                                            "container_memory_usage_bytes"
                                        ]["value"],
                                    }
                                )

    return (
        pd.DataFrame(etcd_cpu_usages, columns=["timestamp", "cpu_usage"]),
        pd.DataFrame(etcd_memory_usages, columns=["timestamp", "memory_usage"]),
        pd.DataFrame(etcd_blkio_usages, columns=["timestamp", "blkio_write"]),
        pd.DataFrame(
            etcd_blkio_read_usages, columns=["timestamp", "blkio_read"]
        ),
        pd.DataFrame(
            etcd_network_read_usages, columns=["timestamp", "network_read"]
        ),
        pd.DataFrame(
            etcd_network_write_usages, columns=["timestamp", "network_write"]
        ),
        pd.DataFrame(apiserver_cpu_usages, columns=["timestamp", "cpu_usage"]),
        pd.DataFrame(
            apiserver_memory_usages, columns=["timestamp", "memory_usage"]
        ),
    )


def process_control_plane_stats(files: List[str]) -> pd.DataFrame:
    util_data = []
    start_time = None
    for control_plane_stats_file in sorted(files):
        with open(control_plane_stats_file, "r") as f:
            stats = json.load(f)

            for stat in stats:
                read_time = stat["read"][:-4] + "Z"
                datetime_obj = datetime.datetime.strptime(
                    read_time, "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                ts = datetime_obj.timestamp()
                curr_cpu_stat = stat["cpu_stats"]
                curr_cpu_usage = curr_cpu_stat["cpu_usage"]["total_usage"]
                curr_system_cpu_usage = curr_cpu_stat["system_cpu_usage"]

                prev_cpu_stat = stat["precpu_stats"]
                prev_cpu_usage = prev_cpu_stat["cpu_usage"]["total_usage"]
                if prev_cpu_usage == 0:
                    start_time = ts
                    continue
                prev_system_cpu_usage = prev_cpu_stat["system_cpu_usage"]

                cpu_util = (
                    (curr_cpu_usage - prev_cpu_usage)
                    / (curr_system_cpu_usage - prev_system_cpu_usage)
                    * 100
                    * curr_cpu_stat["online_cpus"]
                )

                memory_usage = stat["memory_stats"]["usage"]

                read_bytes = 0
                write_bytes = 0
                for blkio_stat in stat["blkio_stats"][
                    "io_service_bytes_recursive"
                ]:
                    if blkio_stat["op"] == "Read":
                        read_bytes += blkio_stat["value"]
                    elif blkio_stat["op"] == "Write":
                        write_bytes += blkio_stat["value"]

                network_read_bytes = 0
                network_write_bytes = 0
                for network_stat in stat["networks"].values():
                    network_read_bytes += network_stat["rx_bytes"]
                    network_write_bytes += network_stat["tx_bytes"]

                util_data.append(
                    {
                        "timestamp": ts - start_time,
                        "cpu_util": cpu_util,
                        "memory_usage": memory_usage,
                        "read_bytes": read_bytes,
                        "write_bytes": write_bytes,
                        "network_read_bytes": network_read_bytes,
                        "network_write_bytes": network_write_bytes,
                    }
                )

    return pd.DataFrame(
        util_data,
        columns=[
            "timestamp",
            "cpu_util",
            "memory_usage",
            "read_bytes",
            "write_bytes",
            "network_read_bytes",
            "network_write_bytes",
        ],
        index=[x["timestamp"] for x in util_data],
    )


def _pod_label(pod_name: str) -> str:
    """Return a stable Deployment name from a pod name by stripping RS and pod hash suffixes."""
    if pod_name == "etcd-anvil-control-plane":
        return "etcd"
    parts = pod_name.rsplit("-", 2)
    return parts[0] if len(parts) == 3 else pod_name


def process_pod_stats(
    files: List[str],
) -> dict:
    """Parse pods_stats JSON files.

    Returns a dict mapping stable pod label → (cpu_df, memory_df).
    The "etcd" key always uses the label "etcd".  All other pods are keyed by
    the Deployment name (pod name with the RS-hash and pod-hash stripped).
    """
    cpu_usages: dict = {}
    memory_usages: dict = {}
    start_time = None
    for pod_stat_file in sorted(files):
        with open(pod_stat_file, "r") as f:
            stats = json.load(f)

        for stat in stats:
            for pod_name, pod_stat in stat.items():
                ts_raw = datetime.datetime.strptime(
                    pod_stat["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
                ).timestamp()
                if start_time is None:
                    start_time = ts_raw
                timestamp = ts_raw - start_time
                cpu_usage = kubernetes.utils.parse_quantity(
                    pod_stat["containers"][0]["usage"]["cpu"]
                )
                memory_usage = kubernetes.utils.parse_quantity(
                    pod_stat["containers"][0]["usage"]["memory"]
                )
                label = _pod_label(pod_name)
                if label not in cpu_usages:
                    cpu_usages[label] = []
                    memory_usages[label] = []
                cpu_usages[label].append(
                    {"timestamp": timestamp, "cpu_usage": cpu_usage}
                )
                memory_usages[label].append(
                    {"timestamp": timestamp, "memory_usage": memory_usage}
                )

    return {
        label: (
            pd.DataFrame(cpu_usages[label], columns=["timestamp", "cpu_usage"]),
            pd.DataFrame(
                memory_usages[label], columns=["timestamp", "memory_usage"]
            ),
        )
        for label in cpu_usages
    }


def _plot_cpu_memory(
    anvil_cpu_df: pd.DataFrame,
    anvil_mem_df: pd.DataFrame,
    reference_cpu_df: pd.DataFrame,
    reference_mem_df: pd.DataFrame,
    label: str,
    output_dir: str,
):
    fig, ax = plt.subplots()
    ax.plot(
        anvil_cpu_df["timestamp"],
        anvil_cpu_df["cpu_usage"],
        label=f"anvil_{label}_cpu",
    )
    if reference_cpu_df is not None and len(reference_cpu_df) > 0:
        ax.plot(
            reference_cpu_df["timestamp"],
            reference_cpu_df["cpu_usage"],
            label=f"reference_{label}_cpu",
        )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("CPU usage (cores)")
    ax.set_title(f"{label} CPU usage")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, f"{label}_cpu_usage.png"))
    plt.close(fig)
    print(
        f"Metrics Server Anvil {label} CPU usage (cores): {anvil_cpu_df['cpu_usage'].mean():.5f}"
    )
    if reference_cpu_df is not None and len(reference_cpu_df) > 0:
        print(
            f"Metrics Server Reference {label} CPU usage (cores): {reference_cpu_df['cpu_usage'].mean():.5f}"
        )

    fig, ax = plt.subplots()
    ax.plot(
        anvil_mem_df["timestamp"],
        anvil_mem_df["memory_usage"],
        label=f"anvil_{label}_memory",
    )
    if reference_mem_df is not None and len(reference_mem_df) > 0:
        ax.plot(
            reference_mem_df["timestamp"],
            reference_mem_df["memory_usage"],
            label=f"reference_{label}_memory",
        )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("memory usage (bytes)")
    ax.set_title(f"{label} memory usage")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, f"{label}_memory_usage.png"))
    plt.close(fig)
    print(
        f"Metrics Server Anvil {label} memory usage (MB): {anvil_mem_df['memory_usage'].mean()/1024/1024:.5f}"
    )
    if reference_mem_df is not None and len(reference_mem_df) > 0:
        print(
            f"Metrics Server Reference {label} memory usage (MB): {reference_mem_df['memory_usage'].mean()/1024/1024:.5f}"
        )


def plot_metrics_server_data(
    anvil_resource_util_dfs: dict,
    reference_resource_util_dfs: dict,
    output_dir: str,
):
    """Plot CPU/memory for each controller found in anvil stats.

    Both arguments are dicts: label → (cpu_df, memory_df).
    """
    all_labels = list(anvil_resource_util_dfs.keys())
    for label in all_labels:
        anvil_cpu_df, anvil_mem_df = anvil_resource_util_dfs[label]
        if label in reference_resource_util_dfs:
            ref_cpu_df, ref_mem_df = reference_resource_util_dfs[label]
        else:
            ref_cpu_df, ref_mem_df = None, None
        _plot_cpu_memory(
            anvil_cpu_df,
            anvil_mem_df,
            ref_cpu_df,
            ref_mem_df,
            label,
            output_dir,
        )


def plot_etcd_resource_utilization(etcd_df: pd.DataFrame, output_dir: str):
    fig, ax = plt.subplots()
    ax.plot(etcd_df["timestamp"], etcd_df["cpu_usage"], label="etcd_cpu_usage")
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("CPU usage (cores)")
    ax.set_title("etcd CPU usage")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "etcd_cpu_usage.png"))
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(
        etcd_df["timestamp"], etcd_df["memory_usage"], label="etcd_memory_usage"
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("memory usage (bytes)")
    ax.set_title("etcd memory usage")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "etcd_memory_usage.png"))
    plt.close(fig)


def plot_resource_utilization(
    anvil_df: pd.DataFrame, reference_df: pd.DataFrame, output_dir: str
):
    fig, ax = plt.subplots()
    ax.plot(anvil_df["timestamp"], anvil_df["cpu_util"], label="anvil_cpu_util")
    ax.plot(
        reference_df["timestamp"],
        reference_df["cpu_util"],
        label="reference_cpu_util",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("CPU utilization (%)")
    ax.set_title("Control plane node CPU utilization")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "cpu_utilization.png"))
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(
        anvil_df["timestamp"],
        anvil_df["memory_usage"],
        label="anvil_memory_usage",
    )
    ax.plot(
        reference_df["timestamp"],
        reference_df["memory_usage"],
        label="reference_memory_usage",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Memory")
    ax.set_title("Control plane node memory utilization")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "memory_utilization.png"))
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(
        anvil_df["timestamp"], anvil_df["read_bytes"], label="anvil_read_bytes"
    )
    ax.plot(
        reference_df["timestamp"],
        reference_df["read_bytes"],
        label="reference_read_bytes",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Blkio read (bytes)")
    ax.set_title("Control plane blockio read (cumulative)")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "blkio_read_utilization.png"))
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(
        anvil_df["timestamp"],
        anvil_df["write_bytes"],
        label="anvil_write_bytes",
    )
    ax.plot(
        reference_df["timestamp"],
        reference_df["write_bytes"],
        label="reference_write_bytes",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Blkio write (bytes)")
    ax.set_title("Control plane blockio write (cumulative)")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "blkio_write_utilization.png"))
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(
        anvil_df["timestamp"],
        anvil_df["network_read_bytes"],
        label="anvil_read_bytes",
    )
    ax.plot(
        reference_df["timestamp"],
        reference_df["network_read_bytes"],
        label="reference_read_bytes",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Network read (bytes)")
    ax.set_title("Control plane network read (cumulative)")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "network_read_utilization.png"))
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(
        anvil_df["timestamp"],
        anvil_df["network_write_bytes"],
        label="anvil_write_bytes",
    )
    ax.plot(
        reference_df["timestamp"],
        reference_df["network_write_bytes"],
        label="reference_write_bytes",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Network write (bytes)")
    ax.set_title("Control plane network write (cumulative)")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, "network_write_utilization.png"))
    plt.close(fig)


def plot_cadvisor_stats(
    anvil_cadvisor_df_tuple, reference_cadvisor_df_tuple, output_dir
):
    (
        anvil_etcd_cpu_df,
        anvil_etcd_memory_df,
        anvil_etcd_disk_write_df,
        anvil_etcd_blkio_read_usages_df,
        anvil_etcd_network_read_usages_df,
        anvil_etcd_network_write_usages,
        anvil_apiserver_cpu_df,
        anvil_apiserver_memory_df,
    ) = anvil_cadvisor_df_tuple
    (
        reference_etcd_cpu_df,
        reference_etcd_memory_df,
        reference_etcd_disk_write_df,
        reference_etcd_disk_read_df,
        reference_etcd_network_read_df,
        reference_etcd_network_write_df,
        reference_apiserver_cpu_df,
        reference_apiserver_memory_df,
    ) = reference_cadvisor_df_tuple
    plot_cadvisor_cpu_stats(
        anvil_apiserver_cpu_df,
        reference_apiserver_cpu_df,
        output_dir,
        "apiserver",
    )
    plot_cadvisor_memory_stats(
        anvil_apiserver_memory_df,
        reference_apiserver_memory_df,
        output_dir,
        "apiserver",
    )
    print()
    plot_cadvisor_cpu_stats(
        anvil_etcd_cpu_df, reference_etcd_cpu_df, output_dir, "etcd"
    )
    plot_cadvisor_memory_stats(
        anvil_etcd_memory_df, reference_etcd_memory_df, output_dir, "etcd"
    )
    plot_cadvisor_disk_write_stats(
        anvil_etcd_disk_write_df,
        reference_etcd_disk_write_df,
        output_dir,
        "etcd",
    )
    plot_cadvisor_disk_read_stats(
        anvil_etcd_blkio_read_usages_df,
        reference_etcd_disk_read_df,
        output_dir,
        "etcd",
    )
    plot_cadvisor_network_read_stats(
        anvil_etcd_network_read_usages_df,
        reference_etcd_network_read_df,
        output_dir,
        "etcd",
    )
    plot_cadvisor_network_write_stats(
        anvil_etcd_network_write_usages,
        reference_etcd_network_write_df,
        output_dir,
        "etcd",
    )


def plot_cadvisor_cpu_stats(
    anvil_cadvisor_df: pd.DataFrame,
    reference_cadvisor_df: pd.DataFrame,
    output_dir: str,
    container_name: str,
):
    anvil_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    anvil_cadvisor_df = anvil_cadvisor_df.sort_values(by="timestamp")
    anvil_cadvisor_df["cpu_diff"] = anvil_cadvisor_df["cpu_usage"].diff()
    # Calculate the time difference between consecutive rows
    anvil_cadvisor_df["time_diff"] = anvil_cadvisor_df["timestamp"].diff()
    # Calculate CPU time per second
    anvil_cadvisor_df["cpu_time_per_second"] = (
        anvil_cadvisor_df["cpu_diff"] / anvil_cadvisor_df["time_diff"]
    )
    anvil_cpu_mean = anvil_cadvisor_df["cpu_time_per_second"].mean()
    anvil_cpu_std = anvil_cadvisor_df["cpu_time_per_second"].std()
    print(
        f"anvil {container_name} cpu usage (CPU time): {anvil_cpu_mean:.5f} ± {anvil_cpu_std:.5f}"
    )

    reference_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    reference_cadvisor_df = reference_cadvisor_df.sort_values(by="timestamp")
    reference_cadvisor_df["cpu_diff"] = reference_cadvisor_df[
        "cpu_usage"
    ].diff()
    # Calculate the time difference between consecutive rows
    reference_cadvisor_df["time_diff"] = reference_cadvisor_df[
        "timestamp"
    ].diff()
    # Calculate CPU time per second
    reference_cadvisor_df["cpu_time_per_second"] = (
        reference_cadvisor_df["cpu_diff"] / reference_cadvisor_df["time_diff"]
    )
    reference_cpu_mean = reference_cadvisor_df["cpu_time_per_second"].mean()
    reference_cpu_std = reference_cadvisor_df["cpu_time_per_second"].std()
    print(
        f"reference {container_name} cpu usage (CPU time): {reference_cpu_mean:.5f} ± {reference_cpu_std:.5f}"
    )
    cpu_diff = abs(anvil_cpu_mean - reference_cpu_mean)
    within_std = cpu_diff <= max(anvil_cpu_std, reference_cpu_std)
    print(
        f"  difference: {cpu_diff:.5f} {'(within std)' if within_std else '(outside std)'}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        anvil_cadvisor_df["timestamp"],
        anvil_cadvisor_df["cpu_time_per_second"],
        label="anvil_cpu_usage",
    )
    ax.plot(
        reference_cadvisor_df["timestamp"],
        reference_cadvisor_df["cpu_time_per_second"],
        label="reference_cpu_usage",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("CPU time per second")
    ax.set_title(f"{container_name} CPU Time per second")
    ax.set_ylim(bottom=0)
    fig.savefig(
        os.path.join(output_dir, f"{container_name}_cpu_utilization.png")
    )
    plt.close(fig)


def plot_cadvisor_memory_stats(
    anvil_cadvisor_df: pd.DataFrame,
    reference_cadvisor_df: pd.DataFrame,
    output_dir: str,
    container_name: str,
):
    anvil_mem_mean = anvil_cadvisor_df["memory_usage"].mean() / 1024 / 1024
    anvil_mem_std = anvil_cadvisor_df["memory_usage"].std() / 1024 / 1024
    reference_mem_mean = (
        reference_cadvisor_df["memory_usage"].mean() / 1024 / 1024
    )
    reference_mem_std = (
        reference_cadvisor_df["memory_usage"].std() / 1024 / 1024
    )
    print(
        f"anvil {container_name} memory usage (MB): {anvil_mem_mean:.5f} ± {anvil_mem_std:.5f}"
    )
    print(
        f"reference {container_name} memory usage (MB): {reference_mem_mean:.5f} ± {reference_mem_std:.5f}"
    )
    mem_diff = abs(anvil_mem_mean - reference_mem_mean)
    within_std = mem_diff <= max(anvil_mem_std, reference_mem_std)
    print(
        f"  difference: {mem_diff:.5f} MB {'(within std)' if within_std else '(outside std)'}"
    )
    fig, ax = plt.subplots()
    ax.plot(
        anvil_cadvisor_df["timestamp"],
        anvil_cadvisor_df["memory_usage"],
        label="anvil_memory_usage",
    )
    ax.plot(
        reference_cadvisor_df["timestamp"],
        reference_cadvisor_df["memory_usage"],
        label="reference_memory_usage",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Memory consumption (bytes)")
    ax.set_title(f"{container_name} memory consumption")
    ax.set_ylim(bottom=0)
    fig.savefig(
        os.path.join(output_dir, f"{container_name}_memory_consumption.png")
    )
    plt.close(fig)


def plot_cadvisor_disk_write_stats(
    anvil_cadvisor_df: pd.DataFrame,
    reference_cadvisor_df: pd.DataFrame,
    output_dir: str,
    container_name: str,
):
    anvil_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    anvil_cadvisor_df = anvil_cadvisor_df.sort_values(by="timestamp")
    # Calculate the time difference between consecutive rows
    anvil_cadvisor_df["blkio_write_diff"] = anvil_cadvisor_df[
        "blkio_write"
    ].diff()
    anvil_cadvisor_df["time_diff"] = anvil_cadvisor_df["timestamp"].diff()
    # Calculate CPU time per second
    anvil_cadvisor_df["container_fs_writes_bytes_per_second"] = (
        anvil_cadvisor_df["blkio_write_diff"] / anvil_cadvisor_df["time_diff"]
    )
    anvil_disk_write_mean = anvil_cadvisor_df[
        "container_fs_writes_bytes_per_second"
    ].mean()
    anvil_disk_write_std = anvil_cadvisor_df[
        "container_fs_writes_bytes_per_second"
    ].std()
    print(
        f"anvil {container_name} disk write (bytes per second): {anvil_disk_write_mean:.5f} ± {anvil_disk_write_std:.5f}"
    )

    reference_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    reference_cadvisor_df = reference_cadvisor_df.sort_values(by="timestamp")
    reference_cadvisor_df["blkio_write_diff"] = reference_cadvisor_df[
        "blkio_write"
    ].diff()
    # Calculate the time difference between consecutive rows
    reference_cadvisor_df["time_diff"] = reference_cadvisor_df[
        "timestamp"
    ].diff()
    # Calculate CPU time per second
    reference_cadvisor_df["container_fs_writes_bytes_per_second"] = (
        reference_cadvisor_df["blkio_write_diff"]
        / reference_cadvisor_df["time_diff"]
    )
    reference_disk_write_mean = reference_cadvisor_df[
        "container_fs_writes_bytes_per_second"
    ].mean()
    reference_disk_write_std = reference_cadvisor_df[
        "container_fs_writes_bytes_per_second"
    ].std()
    print(
        f"reference {container_name} disk write (bytes per second): {reference_disk_write_mean:.5f} ± {reference_disk_write_std:.5f}"
    )
    disk_write_diff = abs(anvil_disk_write_mean - reference_disk_write_mean)
    within_std = disk_write_diff <= max(
        anvil_disk_write_std, reference_disk_write_std
    )
    print(
        f"  difference: {disk_write_diff:.5f} {'(within std)' if within_std else '(outside std)'}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        anvil_cadvisor_df["timestamp"],
        anvil_cadvisor_df["container_fs_writes_bytes_per_second"],
        label="anvil_block_write",
    )
    ax.plot(
        reference_cadvisor_df["timestamp"],
        reference_cadvisor_df["container_fs_writes_bytes_per_second"],
        label="reference_block_write",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Block write per second")
    ax.set_title(f"{container_name} block write")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, f"{container_name}_blk_write.png"))
    plt.close(fig)


def plot_cadvisor_disk_read_stats(
    anvil_cadvisor_df: pd.DataFrame,
    reference_cadvisor_df: pd.DataFrame,
    output_dir: str,
    container_name: str,
):
    anvil_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    anvil_cadvisor_df = anvil_cadvisor_df.sort_values(by="timestamp")
    # Calculate the time difference between consecutive rows
    anvil_cadvisor_df["blkio_read_diff"] = anvil_cadvisor_df[
        "blkio_read"
    ].diff()
    anvil_cadvisor_df["time_diff"] = anvil_cadvisor_df["timestamp"].diff()
    # Calculate CPU time per second
    anvil_cadvisor_df["container_fs_reads_bytes_per_second"] = (
        anvil_cadvisor_df["blkio_read_diff"] / anvil_cadvisor_df["time_diff"]
    )
    print(
        f"anvil {container_name} disk read (bytes per second): {anvil_cadvisor_df['container_fs_reads_bytes_per_second'].mean():.5f}"
    )

    reference_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    reference_cadvisor_df = reference_cadvisor_df.sort_values(by="timestamp")
    reference_cadvisor_df["blkio_read_diff"] = reference_cadvisor_df[
        "blkio_read"
    ].diff()
    # Calculate the time difference between consecutive rows
    reference_cadvisor_df["time_diff"] = reference_cadvisor_df[
        "timestamp"
    ].diff()
    # Calculate CPU time per second
    reference_cadvisor_df["container_fs_reads_bytes_per_second"] = (
        reference_cadvisor_df["blkio_read_diff"]
        / reference_cadvisor_df["time_diff"]
    )
    print(
        f"reference {container_name} disk read (bytes per second): {reference_cadvisor_df['container_fs_reads_bytes_per_second'].mean():.5f}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        anvil_cadvisor_df["timestamp"],
        anvil_cadvisor_df["container_fs_reads_bytes_per_second"],
        label="anvil_block_read",
    )
    ax.plot(
        reference_cadvisor_df["timestamp"],
        reference_cadvisor_df["container_fs_reads_bytes_per_second"],
        label="reference_block_read",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Block read per second")
    ax.set_title(f"{container_name} block read")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, f"{container_name}_blk_read.png"))
    plt.close(fig)


def plot_cadvisor_network_read_stats(
    anvil_cadvisor_df: pd.DataFrame,
    reference_cadvisor_df: pd.DataFrame,
    output_dir: str,
    container_name: str,
):
    anvil_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    anvil_cadvisor_df = anvil_cadvisor_df.sort_values(by="timestamp")
    # Calculate the time difference between consecutive rows
    anvil_cadvisor_df["network_read_diff"] = anvil_cadvisor_df[
        "network_read"
    ].diff()
    anvil_cadvisor_df["time_diff"] = anvil_cadvisor_df["timestamp"].diff()
    # Calculate CPU time per second
    anvil_cadvisor_df["container_network_receive_bytes_per_second"] = (
        anvil_cadvisor_df["network_read_diff"] / anvil_cadvisor_df["time_diff"]
    )
    print(
        f"anvil {container_name} network receive (bytes per second): {anvil_cadvisor_df['container_network_receive_bytes_per_second'].mean():.5f}"
    )

    reference_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    reference_cadvisor_df = reference_cadvisor_df.sort_values(by="timestamp")
    reference_cadvisor_df["network_read_diff"] = reference_cadvisor_df[
        "network_read"
    ].diff()
    # Calculate the time difference between consecutive rows
    reference_cadvisor_df["time_diff"] = reference_cadvisor_df[
        "timestamp"
    ].diff()
    # Calculate CPU time per second
    reference_cadvisor_df["container_network_receive_bytes_per_second"] = (
        reference_cadvisor_df["network_read_diff"]
        / reference_cadvisor_df["time_diff"]
    )
    print(
        f"reference {container_name} network receive (bytes per second): {reference_cadvisor_df['container_network_receive_bytes_per_second'].mean():.5f}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        anvil_cadvisor_df["timestamp"],
        anvil_cadvisor_df["container_network_receive_bytes_per_second"],
        label="anvil_network_read",
    )
    ax.plot(
        reference_cadvisor_df["timestamp"],
        reference_cadvisor_df["container_network_receive_bytes_per_second"],
        label="reference_network_read",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Network read per second")
    ax.set_title(f"{container_name} network read")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, f"{container_name}_network_read.png"))
    plt.close(fig)


def plot_cadvisor_network_write_stats(
    anvil_cadvisor_df: pd.DataFrame,
    reference_cadvisor_df: pd.DataFrame,
    output_dir: str,
    container_name: str,
):
    anvil_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    anvil_cadvisor_df = anvil_cadvisor_df.sort_values(by="timestamp")
    # Calculate the time difference between consecutive rows
    anvil_cadvisor_df["network_write_diff"] = anvil_cadvisor_df[
        "network_write"
    ].diff()
    anvil_cadvisor_df["time_diff"] = anvil_cadvisor_df["timestamp"].diff()
    # Calculate CPU time per second
    anvil_cadvisor_df["container_network_transmit_bytes_per_second"] = (
        anvil_cadvisor_df["network_write_diff"] / anvil_cadvisor_df["time_diff"]
    )
    print(
        f"anvil {container_name} network send (bytes per second): {anvil_cadvisor_df['container_network_transmit_bytes_per_second'].mean():.5f}"
    )

    reference_cadvisor_df.drop_duplicates(
        subset="timestamp", keep="first", inplace=True
    )
    # Sort the DataFrame by timestamp (if not already sorted)
    reference_cadvisor_df = reference_cadvisor_df.sort_values(by="timestamp")
    reference_cadvisor_df["network_write_diff"] = reference_cadvisor_df[
        "network_write"
    ].diff()
    # Calculate the time difference between consecutive rows
    reference_cadvisor_df["time_diff"] = reference_cadvisor_df[
        "timestamp"
    ].diff()
    # Calculate CPU time per second
    reference_cadvisor_df["container_network_transmit_bytes_per_second"] = (
        reference_cadvisor_df["network_write_diff"]
        / reference_cadvisor_df["time_diff"]
    )
    print(
        f"reference {container_name} network send (bytes per second): {reference_cadvisor_df['container_network_transmit_bytes_per_second'].mean():.5f}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        anvil_cadvisor_df["timestamp"],
        anvil_cadvisor_df["container_network_transmit_bytes_per_second"],
        label="anvil_network_write",
    )
    ax.plot(
        reference_cadvisor_df["timestamp"],
        reference_cadvisor_df["container_network_transmit_bytes_per_second"],
        label="reference_network_write",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("Network write per second")
    ax.set_title(f"{container_name} network write")
    ax.set_ylim(bottom=0)
    fig.savefig(os.path.join(output_dir, f"{container_name}_network_write.png"))
    plt.close(fig)


def process_latency(
    anvil_normal_df: pd.DataFrame,
    anvil_single_operation_df: pd.DataFrame,
    reference_normal_df: pd.DataFrame,
    reference_single_operation_df: pd.DataFrame,
    output_dir: str,
    outer_controller_name: str,
    inner_controller_name: Optional[str] = None,
):
    header = [
        "name",
        "anvil_condition_1_duration",
        "reference_condition_1_duration",
        "anvil_condition_2_duration",
        "reference_condition_2_duration",
    ]

    merged_normal_df = pd.merge(
        anvil_normal_df, reference_normal_df, on="name", how="inner"
    )
    merged_single_operation_df = pd.merge(
        anvil_single_operation_df,
        reference_single_operation_df,
        on="name",
        how="inner",
    )

    has_intermediate = (
        "anvil_intermediate_duration_a" in merged_normal_df.columns
        or "anvil_intermediate_duration_a" in merged_single_operation_df.columns
    ) and (
        "reference_intermediate_duration_a" in merged_normal_df.columns
        or "reference_intermediate_duration_a"
        in merged_single_operation_df.columns
    )

    print(
        merged_single_operation_df[
            merged_single_operation_df.anvil_condition_2_duration > 44
        ]
    )

    # print(f"Number of operations in operation sequence: {len(merged_normal_df)}")
    operation_sequence_table = [header]
    operation_sequence_table.append(
        [
            "mean",
            f"{merged_normal_df['anvil_condition_1_duration'].mean():05.3f}",
            f"{merged_normal_df['reference_condition_1_duration'].mean():05.3f}",
            f"{merged_normal_df['anvil_condition_2_duration'].mean():05.3f}",
            f"{merged_normal_df['reference_condition_2_duration'].mean():05.3f}",
        ]
    )
    operation_sequence_table.append(
        [
            "geomean",
            f"{geometric_mean(merged_normal_df['anvil_condition_1_duration']):05.3f}",
            f"{geometric_mean(merged_normal_df['reference_condition_1_duration']):05.3f}",
            f"{geometric_mean(merged_normal_df['anvil_condition_2_duration']):05.3f}",
            f"{geometric_mean(merged_normal_df['reference_condition_2_duration']):05.3f}",
        ]
    )
    operation_sequence_table.append(
        [
            "min",
            f"{merged_normal_df['anvil_condition_1_duration'].min():05.3f}",
            f"{merged_normal_df['reference_condition_1_duration'].min():05.3f}",
            f"{merged_normal_df['anvil_condition_2_duration'].min():05.3f}",
            f"{merged_normal_df['reference_condition_2_duration'].min():05.3f}",
        ]
    )
    operation_sequence_table.append(
        [
            "max",
            f"{merged_normal_df['anvil_condition_1_duration'].max():05.3f}",
            f"{merged_normal_df['reference_condition_1_duration'].max():05.3f}",
            f"{merged_normal_df['anvil_condition_2_duration'].max():05.3f}",
            f"{merged_normal_df['reference_condition_2_duration'].max():05.3f}",
        ]
    )
    operation_sequence_table.append(
        [
            "std(diff)",
            f"{(merged_normal_df['anvil_condition_1_duration'] - merged_normal_df['reference_condition_1_duration']).std():05.3f}",
            "",
            f"{(merged_normal_df['anvil_condition_2_duration'] - merged_normal_df['reference_condition_2_duration']).std():05.3f}",
            "",
        ]
    )
    operation_sequence_table_str = tabulate.tabulate(
        operation_sequence_table, headers="firstrow"
    )

    single_operation_table = [header]
    single_operation_table.append(
        [
            "mean",
            f"{merged_single_operation_df['anvil_condition_1_duration'].mean():05.3f}",
            f"{merged_single_operation_df['reference_condition_1_duration'].mean():05.3f}",
            f"{merged_single_operation_df['anvil_condition_2_duration'].mean():05.3f}",
            f"{merged_single_operation_df['reference_condition_2_duration'].mean():05.3f}",
        ]
    )
    single_operation_table.append(
        [
            "geomean",
            f"{geometric_mean(merged_single_operation_df['anvil_condition_1_duration']):05.3f}",
            f"{geometric_mean(merged_single_operation_df['reference_condition_1_duration']):05.3f}",
            f"{geometric_mean(merged_single_operation_df['anvil_condition_2_duration']):05.3f}",
            f"{geometric_mean(merged_single_operation_df['reference_condition_2_duration']):05.3f}",
        ]
    )
    single_operation_table.append(
        [
            "min",
            f"{merged_single_operation_df['anvil_condition_1_duration'].min():05.3f}",
            f"{merged_single_operation_df['reference_condition_1_duration'].min():05.3f}",
            f"{merged_single_operation_df['anvil_condition_2_duration'].min():05.3f}",
            f"{merged_single_operation_df['reference_condition_2_duration'].min():05.3f}",
        ]
    )
    single_operation_table.append(
        [
            "max",
            f"{merged_single_operation_df['anvil_condition_1_duration'].max():05.3f}",
            f"{merged_single_operation_df['reference_condition_1_duration'].max():05.3f}",
            f"{merged_single_operation_df['anvil_condition_2_duration'].max():05.3f}",
            f"{merged_single_operation_df['reference_condition_2_duration'].max():05.3f}",
        ]
    )
    single_operation_table.append(
        [
            "std(diff)",
            f"{(merged_single_operation_df['anvil_condition_1_duration'] - merged_single_operation_df['reference_condition_1_duration']).std():05.3f}",
            "",
            f"{(merged_single_operation_df['anvil_condition_2_duration'] - merged_single_operation_df['reference_condition_2_duration']).std():05.3f}",
            "",
        ]
    )
    single_operation_table_str = tabulate.tabulate(
        single_operation_table, headers="firstrow"
    )

    anvil_condition_1_merged = pd.concat(
        [
            merged_normal_df["anvil_condition_1_duration"],
            merged_single_operation_df["anvil_condition_1_duration"],
        ],
        ignore_index=True,
    )
    anvil_condition_2_merged = pd.concat(
        [
            merged_normal_df["anvil_condition_2_duration"],
            merged_single_operation_df["anvil_condition_2_duration"],
        ],
        ignore_index=True,
    )

    reference_condition_1_merged = pd.concat(
        [
            merged_normal_df["reference_condition_1_duration"],
            merged_single_operation_df["reference_condition_1_duration"],
        ],
        ignore_index=True,
    )
    reference_condition_2_merged = pd.concat(
        [
            merged_normal_df["reference_condition_2_duration"],
            merged_single_operation_df["reference_condition_2_duration"],
        ],
        ignore_index=True,
    )

    merged_table = [header]
    merged_table.append(
        [
            "mean",
            f"{anvil_condition_1_merged.mean():05.3f}",
            f"{reference_condition_1_merged.mean():05.3f}",
            f"{anvil_condition_2_merged.mean():05.3f}",
            f"{reference_condition_2_merged.mean():05.3f}",
        ]
    )
    # merged_table.append(
    #     [
    #         "geomean",
    #         f"{geometric_mean(anvil_condition_1_merged):05.3f}",
    #         f"{geometric_mean(reference_condition_1_merged):05.3f}",
    #         f"{geometric_mean(anvil_condition_2_merged):05.3f}",
    #         f"{geometric_mean(reference_condition_2_merged):05.3f}",
    #     ]
    # )
    merged_table.append(
        [
            "min",
            f"{anvil_condition_1_merged.min():05.3f}",
            f"{reference_condition_1_merged.min():05.3f}",
            f"{anvil_condition_2_merged.min():05.3f}",
            f"{reference_condition_2_merged.min():05.3f}",
        ]
    )
    merged_table.append(
        [
            "max",
            f"{anvil_condition_1_merged.max():05.3f}",
            f"{reference_condition_1_merged.max():05.3f}",
            f"{anvil_condition_2_merged.max():05.3f}",
            f"{reference_condition_2_merged.max():05.3f}",
        ]
    )
    condition_1_diff_merged = pd.concat(
        [
            merged_normal_df["anvil_condition_1_duration"]
            - merged_normal_df["reference_condition_1_duration"],
            merged_single_operation_df["anvil_condition_1_duration"]
            - merged_single_operation_df["reference_condition_1_duration"],
        ],
        ignore_index=True,
    )
    condition_2_diff_merged = pd.concat(
        [
            merged_normal_df["anvil_condition_2_duration"]
            - merged_normal_df["reference_condition_2_duration"],
            merged_single_operation_df["anvil_condition_2_duration"]
            - merged_single_operation_df["reference_condition_2_duration"],
        ],
        ignore_index=True,
    )
    merged_table.append(
        [
            "std(diff)",
            f"{condition_1_diff_merged.std():05.3f}",
            "",
            f"{condition_2_diff_merged.std():05.3f}",
            "",
        ]
    )
    merged_table_str = tabulate.tabulate(merged_table, headers="firstrow")

    with open(f"{output_dir}/latency_table.txt", "w") as f:
        f.write(
            f"Number of operations in operation sequence: {len(merged_normal_df)}\n"
        )
        f.write(operation_sequence_table_str)
        f.write("\n\n")
        f.write(
            f"Number of operations in single operation: {len(merged_single_operation_df)}\n"
        )
        f.write(single_operation_table_str)
        f.write("\n\n")
        f.write(
            f"Number of operations in merged: {len(anvil_condition_1_merged)}\n"
        )
        f.write(merged_table_str)

    with open(f"{output_dir}/latency_table.csv", "w") as f:
        writer = csv.writer(f, delimiter="\t")
        for row in operation_sequence_table:
            writer.writerow(row)

        for row in single_operation_table:
            writer.writerow(row)

        for row in merged_table:
            writer.writerow(row)

    plot_latency(
        anvil_condition_1_merged,
        anvil_condition_2_merged,
        reference_condition_1_merged,
        reference_condition_2_merged,
        output_dir,
    )

    if has_intermediate:
        has_c = (
            "anvil_intermediate_duration_c" in merged_normal_df.columns
            or "anvil_intermediate_duration_c"
            in merged_single_operation_df.columns
        ) and (
            "reference_intermediate_duration_c" in merged_normal_df.columns
            or "reference_intermediate_duration_c"
            in merged_single_operation_df.columns
        )
        has_e = (
            "anvil_intermediate_duration_e" in merged_normal_df.columns
            or "anvil_intermediate_duration_e"
            in merged_single_operation_df.columns
        ) and (
            "reference_intermediate_duration_e" in merged_normal_df.columns
            or "reference_intermediate_duration_e"
            in merged_single_operation_df.columns
        )

        inter_header = ["name"]
        if has_e:
            inter_header += [
                "anvil_intermediate_duration_e",
                "reference_intermediate_duration_e",
            ]
        if has_c:
            inter_header += [
                "anvil_intermediate_duration_c",
                "reference_intermediate_duration_c",
            ]
        inter_header += [
            "anvil_intermediate_duration_a",
            "reference_intermediate_duration_a",
            "anvil_intermediate_duration_b",
            "reference_intermediate_duration_b",
        ]

        def _concat_inter(col: str) -> pd.Series:
            parts = []
            for df in (merged_normal_df, merged_single_operation_df):
                if col in df.columns and len(df) > 0:
                    parts.append(df[col])
            return pd.concat(parts, ignore_index=True)

        anvil_inter_a_merged = _concat_inter("anvil_intermediate_duration_a")
        anvil_inter_b_merged = _concat_inter("anvil_intermediate_duration_b")
        reference_inter_a_merged = _concat_inter(
            "reference_intermediate_duration_a"
        )
        reference_inter_b_merged = _concat_inter(
            "reference_intermediate_duration_b"
        )
        if has_c:
            anvil_inter_c_merged = _concat_inter(
                "anvil_intermediate_duration_c"
            )
            reference_inter_c_merged = _concat_inter(
                "reference_intermediate_duration_c"
            )
        if has_e:
            anvil_inter_e_merged = _concat_inter(
                "anvil_intermediate_duration_e"
            )
            reference_inter_e_merged = _concat_inter(
                "reference_intermediate_duration_e"
            )

        def _col_stats(df: pd.DataFrame, col: str) -> list:
            return [
                df[col].mean(),
                geometric_mean(df[col]),
                df[col].min(),
                df[col].max(),
            ]

        def _inter_table_rows(df: pd.DataFrame, header: list) -> list:
            if (
                "anvil_intermediate_duration_a" not in df.columns
                or len(df) == 0
            ):
                return [header]
            df_has_c = (
                "anvil_intermediate_duration_c" in df.columns
                and "reference_intermediate_duration_c" in df.columns
            )
            df_has_e = (
                "anvil_intermediate_duration_e" in df.columns
                and "reference_intermediate_duration_e" in df.columns
            )
            rows = [header]
            stats = ["mean", "geomean", "min", "max"]
            a_a = _col_stats(df, "anvil_intermediate_duration_a")
            a_r = _col_stats(df, "reference_intermediate_duration_a")
            b_a = _col_stats(df, "anvil_intermediate_duration_b")
            b_r = _col_stats(df, "reference_intermediate_duration_b")
            c_a = (
                _col_stats(df, "anvil_intermediate_duration_c")
                if df_has_c
                else None
            )
            c_r = (
                _col_stats(df, "reference_intermediate_duration_c")
                if df_has_c
                else None
            )
            e_a = (
                _col_stats(df, "anvil_intermediate_duration_e")
                if df_has_e
                else None
            )
            e_r = (
                _col_stats(df, "reference_intermediate_duration_e")
                if df_has_e
                else None
            )
            for i, stat in enumerate(stats):
                row = [stat]
                if df_has_e:
                    row += [f"{e_a[i]:05.3f}", f"{e_r[i]:05.3f}"]
                if df_has_c:
                    row += [f"{c_a[i]:05.3f}", f"{c_r[i]:05.3f}"]
                row += [
                    f"{a_a[i]:05.3f}",
                    f"{a_r[i]:05.3f}",
                    f"{b_a[i]:05.3f}",
                    f"{b_r[i]:05.3f}",
                ]
                rows.append(row)
            std_row = ["std(diff)"]
            if df_has_e:
                std_row += [
                    f"{(df['anvil_intermediate_duration_e'] - df['reference_intermediate_duration_e']).std():05.3f}",
                    "",
                ]
            if df_has_c:
                std_row += [
                    f"{(df['anvil_intermediate_duration_c'] - df['reference_intermediate_duration_c']).std():05.3f}",
                    "",
                ]
            std_row += [
                f"{(df['anvil_intermediate_duration_a'] - df['reference_intermediate_duration_a']).std():05.3f}",
                "",
                f"{(df['anvil_intermediate_duration_b'] - df['reference_intermediate_duration_b']).std():05.3f}",
                "",
            ]
            rows.append(std_row)
            return rows

        inter_normal_rows = _inter_table_rows(merged_normal_df, inter_header)
        inter_single_rows = _inter_table_rows(
            merged_single_operation_df, inter_header
        )

        def _diff_series(col_a: str, col_b: str) -> pd.Series:
            parts = []
            for df in (merged_normal_df, merged_single_operation_df):
                if col_a in df.columns and len(df) > 0:
                    parts.append(df[col_a] - df[col_b])
            return (
                pd.concat(parts, ignore_index=True)
                if parts
                else pd.Series(dtype=float)
            )

        inter_a_diff_merged = _diff_series(
            "anvil_intermediate_duration_a", "reference_intermediate_duration_a"
        )
        inter_b_diff_merged = _diff_series(
            "anvil_intermediate_duration_b", "reference_intermediate_duration_b"
        )
        inter_c_diff_merged = (
            _diff_series(
                "anvil_intermediate_duration_c",
                "reference_intermediate_duration_c",
            )
            if has_c
            else None
        )
        inter_e_diff_merged = (
            _diff_series(
                "anvil_intermediate_duration_e",
                "reference_intermediate_duration_e",
            )
            if has_e
            else None
        )

        inter_merged_rows = [inter_header]
        for i, stat in enumerate(["mean", "min", "max"]):
            row = [stat]
            if has_e:
                row += [
                    f"{[anvil_inter_e_merged.mean(), anvil_inter_e_merged.min(), anvil_inter_e_merged.max()][i]:05.3f}",
                    f"{[reference_inter_e_merged.mean(), reference_inter_e_merged.min(), reference_inter_e_merged.max()][i]:05.3f}",
                ]
            if has_c:
                row += [
                    f"{[anvil_inter_c_merged.mean(), anvil_inter_c_merged.min(), anvil_inter_c_merged.max()][i]:05.3f}",
                    f"{[reference_inter_c_merged.mean(), reference_inter_c_merged.min(), reference_inter_c_merged.max()][i]:05.3f}",
                ]
            row += [
                f"{[anvil_inter_a_merged.mean(), anvil_inter_a_merged.min(), anvil_inter_a_merged.max()][i]:05.3f}",
                f"{[reference_inter_a_merged.mean(), reference_inter_a_merged.min(), reference_inter_a_merged.max()][i]:05.3f}",
                f"{[anvil_inter_b_merged.mean(), anvil_inter_b_merged.min(), anvil_inter_b_merged.max()][i]:05.3f}",
                f"{[reference_inter_b_merged.mean(), reference_inter_b_merged.min(), reference_inter_b_merged.max()][i]:05.3f}",
            ]
            inter_merged_rows.append(row)
        std_row = ["std(diff)"]
        if has_e:
            std_row += [f"{inter_e_diff_merged.std():05.3f}", ""]
        if has_c:
            std_row += [f"{inter_c_diff_merged.std():05.3f}", ""]
        std_row += [
            f"{inter_a_diff_merged.std():05.3f}",
            "",
            f"{inter_b_diff_merged.std():05.3f}",
            "",
        ]
        inter_merged_rows.append(std_row)

        with open(f"{output_dir}/intermediate_latency_table.txt", "w") as f:
            f.write(
                f"Number of operations in operation sequence: {len(merged_normal_df)}\n"
            )
            f.write(tabulate.tabulate(inter_normal_rows, headers="firstrow"))
            f.write("\n\n")
            f.write(
                f"Number of operations in single operation: {len(merged_single_operation_df)}\n"
            )
            f.write(tabulate.tabulate(inter_single_rows, headers="firstrow"))
            f.write("\n\n")
            f.write(
                f"Number of operations in merged: {len(anvil_inter_a_merged)}\n"
            )
            f.write(tabulate.tabulate(inter_merged_rows, headers="firstrow"))

        with open(f"{output_dir}/intermediate_latency_table.csv", "w") as f:
            writer = csv.writer(f, delimiter="\t")
            for row in inter_normal_rows:
                writer.writerow(row)
            for row in inter_single_rows:
                writer.writerow(row)
            for row in inter_merged_rows:
                writer.writerow(row)

        plot_intermediate_latency(
            anvil_inter_a_merged,
            anvil_inter_b_merged,
            reference_inter_a_merged,
            reference_inter_b_merged,
            output_dir,
            anvil_inter_c_merged if has_c else None,
            reference_inter_c_merged if has_c else None,
            anvil_inter_e_merged if has_e else None,
            reference_inter_e_merged if has_e else None,
        )

    ###########################################################
    # Reconcile / end-to-end table (welder-table-2.txt)
    ###########################################################

    merged_all_df = pd.concat(
        [merged_normal_df, merged_single_operation_df], ignore_index=True
    )

    outer_reconcile = _paired_stats(
        merged_all_df,
        "anvil_condition_1_duration",
        "reference_condition_1_duration",
    )
    outer_e2e = _paired_stats(
        merged_all_df,
        "anvil_condition_2_duration",
        "reference_condition_2_duration",
    )

    new_rows = []
    if (
        inner_controller_name is not None
        and "anvil_intermediate_duration_a" in merged_all_df.columns
        and "reference_intermediate_duration_a" in merged_all_df.columns
    ):
        inner_reconcile = _paired_stats(
            merged_all_df,
            "anvil_intermediate_duration_a",
            "reference_intermediate_duration_a",
        )
        # The child controller (RS/STS) only has a reconcile time for the
        # trials where it actually observed pod creation; restrict the
        # end-to-end stats to that same set of trials so the paired diff is
        # meaningful.
        inner_trials_df = merged_all_df.dropna(
            subset=[
                "anvil_intermediate_duration_a",
                "reference_intermediate_duration_a",
            ]
        )
        inner_e2e = _paired_stats(
            inner_trials_df,
            "anvil_condition_2_duration",
            "reference_condition_2_duration",
        )
        new_rows.append(
            {
                "name": inner_controller_name,
                "reconcile": inner_reconcile,
                "e2e": inner_e2e,
            }
        )
    new_rows.append(
        {
            "name": outer_controller_name,
            "reconcile": outer_reconcile,
            "e2e": outer_e2e,
        }
    )
    controller_table_rows.extend(new_rows)


def plot_latency(
    anvil_condition_1_merged,
    anvil_condition_2_merged,
    reference_condition_1_merged,
    reference_condition_2_merged,
    output_dir: str,
):
    x = anvil_condition_1_merged.sort_values()
    x2 = reference_condition_1_merged.sort_values()
    y = np.arange(1, len(x) + 1) / len(x)
    fig, ax = plt.subplots()
    ax.plot(x, y, marker=".", label="anvil")
    ax.plot(x2, y, marker=".", label="reference")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("CDF")
    ax.set_title("CDF of time for condition 1")
    ax.set_ylim(bottom=0)
    fig.legend()
    fig.savefig(f"{output_dir}/latency-1.png")

    x = anvil_condition_2_merged.sort_values()
    x2 = reference_condition_2_merged.sort_values()
    y = np.arange(1, len(x) + 1) / len(x)
    fig, ax = plt.subplots()
    ax.plot(x, y, marker=".", label="anvil")
    ax.plot(x2, y, marker=".", label="reference")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("CDF")
    ax.set_title("CDF of time for condition 2")
    ax.set_ylim(bottom=0)
    fig.legend()
    fig.savefig(f"{output_dir}/latency-2.png")
    plt.close(fig)


def plot_intermediate_latency(
    anvil_inter_a_merged,
    anvil_inter_b_merged,
    reference_inter_a_merged,
    reference_inter_b_merged,
    output_dir: str,
    anvil_inter_c_merged=None,
    reference_inter_c_merged=None,
    anvil_inter_e_merged=None,
    reference_inter_e_merged=None,
):
    if (
        anvil_inter_e_merged is not None
        and reference_inter_e_merged is not None
    ):
        x = anvil_inter_e_merged.sort_values()
        x2 = reference_inter_e_merged.sort_values()
        y = np.arange(1, len(x) + 1) / len(x)
        fig, ax = plt.subplots()
        ax.plot(x, y, marker=".", label="anvil")
        ax.plot(x2, y, marker=".", label="reference")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("CDF")
        ax.set_title("CDF of intermediate duration e (condition_5 - start_ts)")
        ax.set_ylim(bottom=0)
        fig.legend()
        fig.savefig(f"{output_dir}/intermediate-latency-e.png")
        plt.close(fig)

    if (
        anvil_inter_c_merged is not None
        and reference_inter_c_merged is not None
    ):
        x = anvil_inter_c_merged.sort_values()
        x2 = reference_inter_c_merged.sort_values()
        y = np.arange(1, len(x) + 1) / len(x)
        fig, ax = plt.subplots()
        ax.plot(x, y, marker=".", label="anvil")
        ax.plot(x2, y, marker=".", label="reference")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("CDF")
        ax.set_title(
            "CDF of intermediate duration c (condition_4 - condition_1)"
        )
        ax.set_ylim(bottom=0)
        fig.legend()
        fig.savefig(f"{output_dir}/intermediate-latency-c.png")
        plt.close(fig)

    x = anvil_inter_a_merged.sort_values()
    x2 = reference_inter_a_merged.sort_values()
    y = np.arange(1, len(x) + 1) / len(x)
    fig, ax = plt.subplots()
    ax.plot(x, y, marker=".", label="anvil")
    ax.plot(x2, y, marker=".", label="reference")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("CDF")
    ax.set_title("CDF of intermediate duration a (condition_3 - condition_1)")
    ax.set_ylim(bottom=0)
    fig.legend()
    fig.savefig(f"{output_dir}/intermediate-latency-a.png")
    plt.close(fig)

    x = anvil_inter_b_merged.sort_values()
    x2 = reference_inter_b_merged.sort_values()
    y = np.arange(1, len(x) + 1) / len(x)
    fig, ax = plt.subplots()
    ax.plot(x, y, marker=".", label="anvil")
    ax.plot(x2, y, marker=".", label="reference")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("CDF")
    ax.set_title("CDF of intermediate duration b (condition_2 - condition_1)")
    ax.set_ylim(bottom=0)
    fig.legend()
    fig.savefig(f"{output_dir}/intermediate-latency-b.png")
    plt.close(fig)


def process_testrun(
    testrun_dir: str,
    outer_controller_name: str,
    inner_controller_name: Optional[str] = None,
):
    anvil_normal_measturement_result_files = glob.glob(
        f"{testrun_dir}/anvil/trial-normal/measurement_result_*.json"
    )
    anvil_normal_cadvisor_stats_files = glob.glob(
        f"{testrun_dir}/anvil/trial-normal/control_plane_stats/cadvisor_stats.*.json"
    )
    anvil_normal_pods_stats_files = glob.glob(
        f"{testrun_dir}/anvil/trial-normal/control_plane_stats/pods_stats.*.json"
    )
    anvil_single_operation_measturement_result_files = glob.glob(
        f"{testrun_dir}/anvil/trial-single-operation/measurement_result_*.json"
    )
    anvil_single_operation_cadvisor_stats_files = glob.glob(
        f"{testrun_dir}/anvil/trial-single-operation/control_plane_stats/cadvisor_stats.*.json"
    )
    anvil_single_operation_pods_stats_files = glob.glob(
        f"{testrun_dir}/anvil/trial-single-operation/control_plane_stats/pods_stats.*.json"
    )

    anvil_normal_cadvisor_stats_df = process_cadvisor(
        anvil_normal_cadvisor_stats_files
    )
    anvil_normal_cadvisor_stats_df = process_cadvisor(
        anvil_single_operation_cadvisor_stats_files
    )
    anvil_normal_pods_stats_dfs = process_pod_stats(
        anvil_normal_pods_stats_files
    )
    anvil_normal_pods_stats_dfs = process_pod_stats(
        anvil_single_operation_pods_stats_files
    )

    reference_normal_measturement_result_files = glob.glob(
        f"{testrun_dir}/reference/trial-normal/measurement_result_*.json"
    )
    reference_normal_cadvisor_stats_files = glob.glob(
        f"{testrun_dir}/reference/trial-normal/control_plane_stats/cadvisor_stats.*.json"
    )
    reference_normal_pods_stats_files = glob.glob(
        f"{testrun_dir}/reference/trial-normal/control_plane_stats/pods_stats.*.json"
    )
    reference_single_operation_measturement_result_files = glob.glob(
        f"{testrun_dir}/reference/trial-single-operation/measurement_result_*.json"
    )
    reference_single_operation_cadvisor_stats_files = glob.glob(
        f"{testrun_dir}/reference/trial-single-operation/control_plane_stats/cadvisor_stats.*.json"
    )
    reference_single_operation_pods_stats_files = glob.glob(
        f"{testrun_dir}/reference/trial-single-operation/control_plane_stats/pods_stats.*.json"
    )

    reference_normal_cadvisor_stats_df = process_cadvisor(
        reference_normal_cadvisor_stats_files
    )
    reference_normal_cadvisor_stats_df = process_cadvisor(
        reference_single_operation_cadvisor_stats_files
    )
    reference_normal_pods_stats_dfs = process_pod_stats(
        reference_normal_pods_stats_files
    )
    reference_normal_pods_stats_dfs = process_pod_stats(
        reference_single_operation_pods_stats_files
    )

    plot_cadvisor_stats(
        anvil_normal_cadvisor_stats_df,
        reference_normal_cadvisor_stats_df,
        testrun_dir,
    )
    plot_metrics_server_data(
        anvil_normal_pods_stats_dfs,
        reference_normal_pods_stats_dfs,
        testrun_dir,
    )

    anvil_normal_df = process_ts(anvil_normal_measturement_result_files)
    anvil_normal_df.rename(
        columns={
            "condition_1_duration": "anvil_condition_1_duration",
            "condition_2_duration": "anvil_condition_2_duration",
            "intermediate_duration_a": "anvil_intermediate_duration_a",
            "intermediate_duration_b": "anvil_intermediate_duration_b",
            "intermediate_duration_c": "anvil_intermediate_duration_c",
            "intermediate_duration_e": "anvil_intermediate_duration_e",
        },
        inplace=True,
    )
    anvil_single_operation_df = process_ts(
        anvil_single_operation_measturement_result_files
    )
    anvil_single_operation_df.rename(
        columns={
            "condition_1_duration": "anvil_condition_1_duration",
            "condition_2_duration": "anvil_condition_2_duration",
            "intermediate_duration_a": "anvil_intermediate_duration_a",
            "intermediate_duration_b": "anvil_intermediate_duration_b",
            "intermediate_duration_c": "anvil_intermediate_duration_c",
            "intermediate_duration_e": "anvil_intermediate_duration_e",
        },
        inplace=True,
    )
    reference_normal_df = process_ts(reference_normal_measturement_result_files)
    reference_normal_df.rename(
        columns={
            "condition_1_duration": "reference_condition_1_duration",
            "condition_2_duration": "reference_condition_2_duration",
            "intermediate_duration_a": "reference_intermediate_duration_a",
            "intermediate_duration_b": "reference_intermediate_duration_b",
            "intermediate_duration_c": "reference_intermediate_duration_c",
            "intermediate_duration_e": "reference_intermediate_duration_e",
        },
        inplace=True,
    )
    reference_single_operation_df = process_ts(
        reference_single_operation_measturement_result_files
    )
    reference_single_operation_df.rename(
        columns={
            "condition_1_duration": "reference_condition_1_duration",
            "condition_2_duration": "reference_condition_2_duration",
            "intermediate_duration_a": "reference_intermediate_duration_a",
            "intermediate_duration_b": "reference_intermediate_duration_b",
            "intermediate_duration_c": "reference_intermediate_duration_c",
            "intermediate_duration_e": "reference_intermediate_duration_e",
        },
        inplace=True,
    )

    process_latency(
        anvil_normal_df,
        anvil_single_operation_df,
        reference_normal_df,
        reference_single_operation_df,
        testrun_dir,
        outer_controller_name,
        inner_controller_name,
    )


def _fmt_diff(mean: float, std: float) -> str:
    return f"{mean:.2f}±{std:.2f}"


def format_controller_table(rows: list) -> str:
    header = [
        "Controller",
        "reconcile Verified",
        "reconcile Ref.",
        "reconcile Diff",
        "End-to-end Verified",
        "End-to-end Ref.",
        "End-to-end Diff",
    ]
    table = [header]
    for row in rows:
        r_verified, r_ref, r_diff_mean, r_diff_std = row["reconcile"]
        e_verified, e_ref, e_diff_mean, e_diff_std = row["e2e"]
        table.append(
            [
                row["name"],
                f"{r_verified:.2f}",
                f"{r_ref:.2f}",
                _fmt_diff(r_diff_mean, r_diff_std),
                f"{e_verified:.2f}",
                f"{e_ref:.2f}",
                _fmt_diff(e_diff_mean, e_diff_std),
            ]
        )
    return tabulate.tabulate(table, headers="firstrow", tablefmt="github")


def main():
    if os.path.exists("testrun-vdeployment-performance"):
        process_testrun(
            "testrun-vdeployment-performance",
            "Deployment",
            "ReplicaSet",
        )
        print()
        print()
    else:
        print("testrun-vdeployment-performance does not exist")

    if os.path.exists("testrun-rabbitmq-performance"):
        process_testrun(
            "testrun-rabbitmq-performance", "RabbitMQ", "StatefulSet"
        )
        print()
        print()
    else:
        print("testrun-rabbitmq-performance does not exist")

    table_str = format_controller_table(controller_table_rows)
    print(table_str)
    with open("welder-table-2.txt", "w", encoding="utf-8") as f:
        f.write(table_str)


main()
