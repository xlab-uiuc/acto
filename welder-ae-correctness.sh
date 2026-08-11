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
# counts; this script mirrors that with a configurable round count per
# category. Defaults (4 rounds individual/correlated, 6 rounds pod-crash)
# are the closest integer match to the paper's counts given the fixed
# 102-trial (vdeployment) / 17-trial (rabbitmq) corpora in welder-ae-data:
#   individual:  4 * (102+102+17+17) =  952  (paper: 868)
#   correlated:  4 * (102+17)        =  476  (paper: 434)
#   pod-crash:   6 * (102+17)        =  714  (paper: 677)
# These are approximations, not exact reproductions -- say so when reporting.

set -euo pipefail
cd "$(dirname "$0")"

INDIVIDUAL_CORRELATED_ROUNDS="${1:-4}"
POD_CRASH_ROUNDS="${2:-6}"

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

for i in $(seq 1 "$INDIVIDUAL_CORRELATED_ROUNDS"); do
    echo "--- individual/correlated crash round $i/$INDIVIDUAL_CORRELATED_ROUNDS ---"
    run_fi data/vdeployment-controller/v0/config.json chactos/vdeployment.json \
        testrun-vdeployment "testrun-vdeployment-fi-r$i"
    run_fi data/vdeployment-controller/v0/config.json chactos/vreplicaset.json \
        testrun-vdeployment "testrun-vdeployment-replicaset-fi-r$i"
    run_fi data/vdeployment-controller/v0/config.json chactos/vdeployment-correlated.json \
        testrun-vdeployment "testrun-vdeployment-correlated-fi-r$i"
    run_fi data/anvil-rabbitmq-controller/config.json chactos/rabbitmq-controller.json \
        testrun-rabbitmq "testrun-rabbitmq-fi-r$i"
    run_fi data/anvil-rabbitmq-controller/config.json chactos/vstatefulset.json \
        testrun-rabbitmq "testrun-rabbitmq-vstatefulset-fi-r$i"
    run_fi data/anvil-rabbitmq-controller/config.json chactos/rabbitmq-controller-correlated.json \
        testrun-rabbitmq "testrun-rabbitmq-correlated-fi-r$i"
    ALL_WORKDIRS+=(
        "testrun-vdeployment-fi-r$i" "testrun-vdeployment-replicaset-fi-r$i"
        "testrun-vdeployment-correlated-fi-r$i" "testrun-rabbitmq-fi-r$i"
        "testrun-rabbitmq-vstatefulset-fi-r$i" "testrun-rabbitmq-correlated-fi-r$i"
    )
done

for i in $(seq 1 "$POD_CRASH_ROUNDS"); do
    echo "--- pod-crash round $i/$POD_CRASH_ROUNDS ---"
    run_fi data/vdeployment-controller/v0/config.json chactos/vdeployment-pod-crash-rand.json \
        testrun-vdeployment "testrun-vdeployment-pod-crash-rand-fi-r$i"
    run_fi data/anvil-rabbitmq-controller/config.json chactos/rabbitmq-controller-pod-crash-rand.json \
        testrun-rabbitmq "testrun-rabbitmq-pod-crash-rand-fi-r$i"
    ALL_WORKDIRS+=(
        "testrun-vdeployment-pod-crash-rand-fi-r$i" "testrun-rabbitmq-pod-crash-rand-fi-r$i"
    )
done

echo "=== Phase 3: summarizing results ==="
python3 welder-ae-correctness-summary.py "${ALL_WORKDIRS[@]}" | tee welder-table-correctness.txt
