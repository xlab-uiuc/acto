#!/bin/bash
#
# Reproduces the paper's Controller Correctness claim (eval.tex, Section 5.2):
# 629 functional tests (Acto CR-mutation testing), 1302 controller-crash
# tests (Sieve-style, incl. 434 correlated crashes of two interacting
# controllers), and 677 Pod-crash tests, with 0 oracle violations expected.
#
# chactos has no "number of tests" flag: one run against a testrun-dir
# produces exactly one test per CR-mutation trial in that dir (see
# acto/post_process/post_process.py). Fault injection is randomized, so the
# original campaign was run multiple times to accumulate its reported
# counts; this script mirrors that with per-corpus round counts.
#
# welder-ae-data has two fixed trial corpora: testrun-vdeployment (102
# trials) and testrun-rabbitmq (17 trials). Since 102 = 6*17, any integer
# combination of rounds against them is a multiple of 17, so exact target
# reproduction isn't possible -- these round counts are the closest integer
# fit, biased toward fewer rounds against the 6x-larger vdeployment corpus:
#   individual:  1*(102+102) + 20*(17+17) =  884  (paper: 868, +1.8%)
#   correlated:  1*102       + 20*17      =  442  (paper: 434, +1.8%)
#   pod-crash:   1*102       + 34*17      =  680  (paper: 677, +0.4%)
# Approximations, not exact reproductions -- say so when reporting.

set -euo pipefail
cd "$(dirname "$0")"

# Rounds against the 102-trial vdeployment corpus (vdeployment.json,
# vreplicaset.json, vdeployment-correlated.json, vdeployment-pod-crash-rand.json)
VDEPLOYMENT_ROUNDS="${1:-1}"
# Rounds against the 17-trial rabbitmq corpus for individual/correlated configs
# (rabbitmq-controller.json, vstatefulset.json, rabbitmq-controller-correlated.json)
RABBITMQ_ROUNDS="${2:-20}"
# Rounds against the 17-trial rabbitmq corpus for the pod-crash config
# (rabbitmq-controller-pod-crash-rand.json)
RABBITMQ_POD_CRASH_ROUNDS="${3:-34}"

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
    if [ -d "$workdir" ]; then
        echo "$workdir already exists, skipping"
        return
    fi
    python3 -m chactos --config "$config" --fi-config "$fi_config" \
        --testrun-dir "$testrun_dir" --workdir "$workdir" --num-workers 6
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
