#!/bin/bash
#
# Reproduces the paper's Controller Correctness claim (eval.tex Section 5.2).
# Round counts are the closest integer approximation of the paper's reported
# 868/434/677 test counts, not an exact reproduction (chactos has no sample
# flag -- one run = one test per trial in --testrun-dir).

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v helm >/dev/null 2>&1; then
    echo "error: helm not found on PATH -- chactos requires it to install Chaos Mesh." >&2
    exit 1
fi

VDEPLOYMENT_ROUNDS="${1:-2}"
RABBITMQ_ROUNDS="${2:-14}"
RABBITMQ_POD_CRASH_ROUNDS="${3:-28}"
# chactos does a full cluster teardown/recreate per trial; on spinning disks
# this saturates fast, so keep this low on non-SSD hardware.
CHACTOS_WORKERS="${CHACTOS_WORKERS:-6}"

echo "=== Phase 1: functional testing (629 tests) ==="

if [ ! -d testrun-vdeployment ]; then
    python3 -m acto --config data/vdeployment-controller/v0/config.json \
        --workdir testrun-vdeployment --num-workers 4
else
    echo "testrun-vdeployment already exists, skipping generation"
fi

if [ ! -d testrun-rabbitmq ]; then
    python3 -m acto --config data/anvil-rabbitmq-controller/config.json \
        --workdir testrun-rabbitmq --num-workers 4
else
    echo "testrun-rabbitmq already exists, skipping generation"
fi

echo "=== Phase 2: fault injection testing ==="

run_fi() {
    local config="$1" fi_config="$2" testrun_dir="$3" workdir="$4"
    local expected actual
    expected=$(find -L "$testrun_dir" -mindepth 1 -maxdepth 1 -type d | wc -l)
    actual=0
    if [ -d "$workdir" ]; then
        actual=$(find "$workdir" -mindepth 1 -maxdepth 1 -type d | wc -l)
    fi
    if [ "$actual" -ge "$expected" ]; then
        echo "$workdir already has $actual/$expected trials, skipping"
        return
    fi
    if [ -d "$workdir" ]; then
        echo "$workdir has only $actual/$expected trials -- wiping and redoing"
        rm -rf "$workdir"
    fi
    python3 -m chactos --config "$config" --fi-config "$fi_config" \
        --testrun-dir "$testrun_dir" --workdir "$workdir" --num-workers "$CHACTOS_WORKERS"
}

ALL_WORKDIRS=()

echo "--- vdeployment-corpus individual/correlated crashes ($VDEPLOYMENT_ROUNDS round(s)) ---"
for i in $(seq 1 "$VDEPLOYMENT_ROUNDS"); do
    run_fi data/vdeployment-controller/v0/config.json chactos/vdeployment.json \
        testrun-vdeployment "testrun-vdeployment-fi-r$i"
    run_fi data/vdeployment-controller/v0/config.json chactos/vreplicaset.json \
        testrun-vdeployment "testrun-vdeployment-replicaset-fi-r$i"
    run_fi data/vdeployment-controller/v0/config.json chactos/vdeployment-correlated.json \
        testrun-vdeployment "testrun-vdeployment-correlated-fi-r$i"
    ALL_WORKDIRS+=(
        "testrun-vdeployment-fi-r$i" "testrun-vdeployment-replicaset-fi-r$i"
        "testrun-vdeployment-correlated-fi-r$i"
    )
done

echo "--- rabbitmq-corpus individual/correlated crashes ($RABBITMQ_ROUNDS round(s)) ---"
for i in $(seq 1 "$RABBITMQ_ROUNDS"); do
    run_fi data/anvil-rabbitmq-controller/config.json chactos/rabbitmq-controller.json \
        testrun-rabbitmq "testrun-rabbitmq-fi-r$i"
    run_fi data/anvil-rabbitmq-controller/config.json chactos/vstatefulset.json \
        testrun-rabbitmq "testrun-rabbitmq-vstatefulset-fi-r$i"
    run_fi data/anvil-rabbitmq-controller/config.json chactos/rabbitmq-controller-correlated.json \
        testrun-rabbitmq "testrun-rabbitmq-correlated-fi-r$i"
    ALL_WORKDIRS+=(
        "testrun-rabbitmq-fi-r$i" "testrun-rabbitmq-vstatefulset-fi-r$i"
        "testrun-rabbitmq-correlated-fi-r$i"
    )
done

echo "--- vdeployment-corpus pod-crash ($VDEPLOYMENT_ROUNDS round(s)) ---"
for i in $(seq 1 "$VDEPLOYMENT_ROUNDS"); do
    run_fi data/vdeployment-controller/v0/config.json chactos/vdeployment-pod-crash-rand.json \
        testrun-vdeployment "testrun-vdeployment-pod-crash-rand-fi-r$i"
    ALL_WORKDIRS+=("testrun-vdeployment-pod-crash-rand-fi-r$i")
done

echo "--- rabbitmq-corpus pod-crash ($RABBITMQ_POD_CRASH_ROUNDS round(s)) ---"
for i in $(seq 1 "$RABBITMQ_POD_CRASH_ROUNDS"); do
    run_fi data/anvil-rabbitmq-controller/config.json chactos/rabbitmq-controller-pod-crash-rand.json \
        testrun-rabbitmq "testrun-rabbitmq-pod-crash-rand-fi-r$i"
    ALL_WORKDIRS+=("testrun-rabbitmq-pod-crash-rand-fi-r$i")
done

echo "=== Phase 3: summarizing results ==="
python3 welder-ae-correctness-summary.py "${ALL_WORKDIRS[@]}" | tee welder-table-correctness.txt
