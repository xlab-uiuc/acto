"""Process the time series data collected from the experiment."""

import csv
import datetime
import glob
import json
import os
from typing import List, Tuple

import kubernetes
import numpy as np
import pandas as pd
import tabulate
from matplotlib import pyplot as plt
from scipy import stats

ineffective_files = set()

anvil_table = [
    [
        "Controller",
        "Verified (Anvil) Mean",
        "Verified (Anvil) Min",
        "Reference (unverified) Mean",
        "Reference (unverified) Min",
    ],
]


def process_ts(files: List[str]) -> pd.DataFrame:
    condition_durations = []
    for ts_datafile in sorted(files):
        with open(ts_datafile, "r") as f:
            data = json.load(f)

            condition_2_duration = (
                data["condition_2_ts"] - data["condition_1_ts"]
            )
            if condition_2_duration < data["condition_1_ts"] - data["start_ts"]:
                # print(os.path.basename(ts_datafile))
                continue
            # if data['condition_1_ts'] - data['start_ts'] > 1:
            #     print(os.path.basename(ts_datafile))
            #     continue
            condition_durations.append(
                {
                    "name": os.path.basename(ts_datafile),
                    "condition_1_duration": data["condition_1_ts"]
                    - data["start_ts"],
                    "condition_2_duration": condition_2_duration,
                }
            )

    return pd.DataFrame(
        condition_durations,
        columns=["name", "condition_1_duration", "condition_2_duration"],
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
                        etcd_cpu_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_cpu_usage_seconds_total"
                                ]["timestamp"]
                                - start_time,
                                "cpu_usage": container_stat[
                                    "container_cpu_usage_seconds_total"
                                ]["value"],
                            }
                        )
                        etcd_memory_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_memory_usage_bytes"
                                ]["timestamp"]
                                - start_time,
                                "memory_usage": container_stat[
                                    "container_memory_usage_bytes"
                                ]["value"],
                            }
                        )
                        etcd_blkio_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_fs_writes_bytes_total"
                                ]["timestamp"]
                                - start_time,
                                "blkio_write": container_stat[
                                    "container_fs_writes_bytes_total"
                                ]["value"],
                            }
                        )
                        etcd_blkio_read_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_fs_reads_bytes_total"
                                ]["timestamp"]
                                - start_time,
                                "blkio_read": container_stat[
                                    "container_fs_reads_bytes_total"
                                ]["value"],
                            }
                        )
                        etcd_network_read_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_network_receive_bytes_total"
                                ]["timestamp"]
                                - start_time,
                                "network_read": container_stat[
                                    "container_network_receive_bytes_total"
                                ]["value"],
                            }
                        )
                        etcd_network_write_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_network_transmit_bytes_total"
                                ]["timestamp"]
                                - start_time,
                                "network_write": container_stat[
                                    "container_network_transmit_bytes_total"
                                ]["value"],
                            }
                        )
                    elif container_name == "kube-apiserver":
                        apiserver_cpu_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_cpu_usage_seconds_total"
                                ]["timestamp"]
                                - start_time,
                                "cpu_usage": container_stat[
                                    "container_cpu_usage_seconds_total"
                                ]["value"],
                            }
                        )
                        apiserver_memory_usages.append(
                            {
                                "timestamp": container_stat[
                                    "container_memory_usage_bytes"
                                ]["timestamp"]
                                - start_time,
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


def process_pod_stats(files: List[str]) -> pd.DataFrame:
    etcd_cpu_usages = []
    etcd_memory_usages = []
    operator_cpu_usages = []
    operator_memory_usages = []
    start_time = None
    for pod_stat_file in sorted(files):
        with open(pod_stat_file, "r") as f:
            stats = json.load(f)

            for stat in stats:
                for pod, pod_stat in stat.items():
                    if pod == "etcd-anvil-control-plane":
                        if start_time is None:
                            start_time = datetime.datetime.strptime(
                                pod_stat["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
                            ).timestamp()

                        timestamp = (
                            datetime.datetime.strptime(
                                pod_stat["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
                            ).timestamp()
                            - start_time
                        )
                        cpu_usage = kubernetes.utils.parse_quantity(
                            pod_stat["containers"][0]["usage"]["cpu"]
                        )
                        memory_usage = kubernetes.utils.parse_quantity(
                            pod_stat["containers"][0]["usage"]["memory"]
                        )

                        etcd_cpu_usages.append(
                            {
                                "timestamp": timestamp,
                                "cpu_usage": cpu_usage,
                            }
                        )
                        etcd_memory_usages.append(
                            {
                                "timestamp": timestamp,
                                "memory_usage": memory_usage,
                            }
                        )
                    else:
                        # assume the other pod is the operator
                        if start_time is None:
                            start_time = datetime.datetime.strptime(
                                pod_stat["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
                            ).timestamp()
                        timestamp = (
                            datetime.datetime.strptime(
                                pod_stat["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
                            ).timestamp()
                            - start_time
                        )
                        cpu_usage = kubernetes.utils.parse_quantity(
                            pod_stat["containers"][0]["usage"]["cpu"]
                        )
                        memory_usage = kubernetes.utils.parse_quantity(
                            pod_stat["containers"][0]["usage"]["memory"]
                        )

                        operator_cpu_usages.append(
                            {
                                "timestamp": timestamp,
                                "cpu_usage": cpu_usage,
                            }
                        )
                        operator_memory_usages.append(
                            {
                                "timestamp": timestamp,
                                "memory_usage": memory_usage,
                            }
                        )

    return (
        pd.DataFrame(etcd_cpu_usages, columns=["timestamp", "cpu_usage"]),
        pd.DataFrame(etcd_memory_usages, columns=["timestamp", "memory_usage"]),
        pd.DataFrame(operator_cpu_usages, columns=["timestamp", "cpu_usage"]),
        pd.DataFrame(
            operator_memory_usages, columns=["timestamp", "memory_usage"]
        ),
    )


def plot_metrics_server_data(
    anvil_resource_util_dfs: pd.DataFrame,
    reference_resource_util_dfs: pd.DataFrame,
    output_dir: str,
):
    (
        etcd_cpu_usage_df,
        etcd_memory_usage_df,
        operator_cpu_usage_df,
        operator_memory_usage_df,
    ) = anvil_resource_util_dfs
    (
        reference_etcd_cpu_usage_df,
        reference_etcd_memory_usage_df,
        reference_operator_cpu_usage_df,
        reference_operator_memory_usage_df,
    ) = reference_resource_util_dfs

    fig, ax = plt.subplots()
    ax.plot(
        etcd_cpu_usage_df["timestamp"],
        etcd_cpu_usage_df["cpu_usage"],
        label="etcd_cpu_usage",
    )
    ax.plot(
        reference_etcd_cpu_usage_df["timestamp"],
        reference_etcd_cpu_usage_df["cpu_usage"],
        label="reference_etcd_cpu_usage",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("CPU usage (cores)")
    ax.set_title("Etcd CPU usage")
    fig.savefig(os.path.join(output_dir, "metrics_server_etcd_cpu_usage.png"))
    plt.close(fig)
    print(
        f"Metrics Server Anvil Etcd CPU usage (CPU time): {etcd_cpu_usage_df['cpu_usage'].mean():.5f}"
    )
    print(
        f"Metrics Server Reference Etcd CPU usage (CPU time): {reference_etcd_cpu_usage_df['cpu_usage'].mean():.5f}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        etcd_memory_usage_df["timestamp"],
        etcd_memory_usage_df["memory_usage"],
        label="etcd_memory_usage",
    )
    ax.plot(
        reference_etcd_memory_usage_df["timestamp"],
        reference_etcd_memory_usage_df["memory_usage"],
        label="reference_etcd_memory_usage",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("memory usage (bytes)")
    ax.set_title("Etcd memory usage")
    fig.savefig(
        os.path.join(output_dir, "metrics_server_etcd_memory_usage.png")
    )
    plt.close(fig)
    print(
        f"Metrics Server Anvil Etcd memory usage (bytes): {etcd_memory_usage_df['memory_usage'].mean():.5f}"
    )
    print(
        f"Metrics Server Reference Etcd memory usage (bytes): {reference_etcd_memory_usage_df['memory_usage'].mean():.5f}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        operator_cpu_usage_df["timestamp"],
        operator_cpu_usage_df["cpu_usage"],
        label="operator_cpu_usage",
    )
    ax.plot(
        reference_operator_cpu_usage_df["timestamp"],
        reference_operator_cpu_usage_df["cpu_usage"],
        label="reference_operator_cpu_usage",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("CPU usage (cores)")
    ax.set_title("Operator CPU usage")
    fig.savefig(os.path.join(output_dir, "operator_cpu_usage.png"))
    plt.close(fig)
    print(
        f"Metrics Server Operator CPU usage (CPU time): {operator_cpu_usage_df['cpu_usage'].mean():.5f}"
    )
    print(
        f"Metrics Server Reference Operator CPU usage (CPU time): {reference_operator_cpu_usage_df['cpu_usage'].mean():.5f}"
    )

    fig, ax = plt.subplots()
    ax.plot(
        operator_memory_usage_df["timestamp"],
        operator_memory_usage_df["memory_usage"],
        label="operator_memory_usage",
    )
    ax.plot(
        reference_operator_memory_usage_df["timestamp"],
        reference_operator_memory_usage_df["memory_usage"],
        label="reference_operator_memory_usage",
    )
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("memory usage (bytes)")
    ax.set_title("Operator memory usage")
    fig.savefig(os.path.join(output_dir, "operator_memory_usage.png"))
    plt.close(fig)
    print(
        f"Metrics Server Operator memory usage (MB): {operator_memory_usage_df['memory_usage'].mean()/1024/1024:.5f}"
    )
    print(
        f"Metrics Server Reference Operator memory usage (MB): {reference_operator_memory_usage_df['memory_usage'].mean()/1024/1024:.5f}"
    )


def plot_etcd_resource_utilization(etcd_df: pd.DataFrame, output_dir: str):
    fig, ax = plt.subplots()
    ax.plot(etcd_df["timestamp"], etcd_df["cpu_usage"], label="etcd_cpu_usage")
    ax.legend()
    ax.set_xlabel("time")
    ax.set_ylabel("CPU usage (cores)")
    ax.set_title("etcd CPU usage")
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
    print(
        f"anvil {container_name} cpu usage (CPU time): {anvil_cadvisor_df['cpu_time_per_second'].mean():.5f}"
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
    print(
        f"reference {container_name} cpu usage (CPU time): {reference_cadvisor_df['cpu_time_per_second'].mean():.5f}"
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
    print(
        f"anvil {container_name} memory usage (MB): {anvil_cadvisor_df['memory_usage'].mean()/1024/1024:.5f}"
    )
    print(
        f"reference {container_name} memory usage (MB): {reference_cadvisor_df['memory_usage'].mean()/1024/1024:.5f}"
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
    print(
        f"anvil {container_name} disk write (bytes per second): {anvil_cadvisor_df['container_fs_writes_bytes_per_second'].mean():.5f}"
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
    print(
        f"reference {container_name} disk write (bytes per second): {reference_cadvisor_df['container_fs_writes_bytes_per_second'].mean():.5f}"
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
    fig.savefig(os.path.join(output_dir, f"{container_name}_network_write.png"))
    plt.close(fig)


def process_latency(
    anvil_normal_df: pd.DataFrame,
    anvil_single_operation_df: pd.DataFrame,
    reference_normal_df: pd.DataFrame,
    reference_single_operation_df: pd.DataFrame,
    output_dir: str,
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
            f"{stats.gmean(merged_normal_df['anvil_condition_1_duration']):05.3f}",
            f"{stats.gmean(merged_normal_df['reference_condition_1_duration']):05.3f}",
            f"{stats.gmean(merged_normal_df['anvil_condition_2_duration']):05.3f}",
            f"{stats.gmean(merged_normal_df['reference_condition_2_duration']):05.3f}",
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
            f"{stats.gmean(merged_single_operation_df['anvil_condition_1_duration']):05.3f}",
            f"{stats.gmean(merged_single_operation_df['reference_condition_1_duration']):05.3f}",
            f"{stats.gmean(merged_single_operation_df['anvil_condition_2_duration']):05.3f}",
            f"{stats.gmean(merged_single_operation_df['reference_condition_2_duration']):05.3f}",
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
    merged_table.append(
        [
            "geomean",
            f"{stats.gmean(anvil_condition_1_merged):05.3f}",
            f"{stats.gmean(reference_condition_1_merged):05.3f}",
            f"{stats.gmean(anvil_condition_2_merged):05.3f}",
            f"{stats.gmean(reference_condition_2_merged):05.3f}",
        ]
    )
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

    ##############################
    # Print the Anvil paper table
    ##############################

    anvil_table.append(
        [
            output_dir,
            f"{anvil_condition_2_merged.mean():05.3f}",
            f"{anvil_condition_2_merged.max():05.3f}",
            f"{reference_condition_2_merged.mean():05.3f}",
            f"{reference_condition_2_merged.max():05.3f}",
        ]
    )


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
    fig.legend()
    fig.savefig(f"{output_dir}/latency-2.png")


def process_testrun(testrun_dir: str):
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
    anvil_single_operation_cadvisor_stats_df = process_cadvisor(
        anvil_single_operation_cadvisor_stats_files
    )
    anvil_normal_pods_stats_dfs = process_pod_stats(
        anvil_normal_pods_stats_files
    )
    anvil_single_operation_pods_stats_dfs = process_pod_stats(
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
    reference_single_operation_cadvisor_stats_df = process_cadvisor(
        reference_single_operation_cadvisor_stats_files
    )
    reference_normal_pods_stats_dfs = process_pod_stats(
        reference_normal_pods_stats_files
    )
    reference_single_operation_pods_stats_dfs = process_pod_stats(
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
            "name": "name",
            "condition_1_duration": "anvil_condition_1_duration",
            "condition_2_duration": "anvil_condition_2_duration",
        },
        inplace=True,
    )
    anvil_single_operation_df = process_ts(
        anvil_single_operation_measturement_result_files
    )
    anvil_single_operation_df.rename(
        columns={
            "name": "name",
            "condition_1_duration": "anvil_condition_1_duration",
            "condition_2_duration": "anvil_condition_2_duration",
        },
        inplace=True,
    )
    reference_normal_df = process_ts(reference_normal_measturement_result_files)
    reference_normal_df.rename(
        columns={
            "name": "name",
            "condition_1_duration": "reference_condition_1_duration",
            "condition_2_duration": "reference_condition_2_duration",
        },
        inplace=True,
    )
    reference_single_operation_df = process_ts(
        reference_single_operation_measturement_result_files
    )
    reference_single_operation_df.rename(
        columns={
            "name": "name",
            "condition_1_duration": "reference_condition_1_duration",
            "condition_2_duration": "reference_condition_2_duration",
        },
        inplace=True,
    )

    process_latency(
        anvil_normal_df,
        anvil_single_operation_df,
        reference_normal_df,
        reference_single_operation_df,
        testrun_dir,
    )


def main():
    process_testrun("testrun-anvil-zk-performance")
    print()
    print()
    process_testrun("testrun-anvil-rabbitmq-performance")
    print()
    print()
    process_testrun("testrun-anvil-fluent-performance")
    print()
    print()

    print(tabulate.tabulate(anvil_table, headers="firstrow"))
    with open("anvil-table-3.txt", "w", encoding="utf-8") as f:
        f.write(tabulate.tabulate(anvil_table, headers="firstrow"))


main()
