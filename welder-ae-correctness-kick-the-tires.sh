#!/bin/bash
#
# Small-scale sanity check for welder-ae-correctness.sh: randomly samples
# a few trials instead of running the full campaign.

set -euo pipefail
cd "$(dirname "$0")"

VDEPLOYMENT_SAMPLE_SIZE="${1:-5}"
RABBITMQ_SAMPLE_SIZE="${2:-3}"
NUM_WORKERS="${3:-1}"

sample_corpus() {
    local src="$1" dest="$2" n="$3"
    rm -rf "$dest"
    mkdir -p "$dest"
    find -L "$src" -mindepth 1 -maxdepth 1 -type d -name 'trial-*' \
        | shuf -n "$n" \
        | while read -r t; do
            ln -sfn "$(realpath "$t")" "$dest/$(basename "$t")"
        done
    echo "$dest: $(find -L "$dest" -mindepth 1 -maxdepth 1 -type d | wc -l) randomly-sampled trials"
}

echo "=== Sampling trials ==="
sample_corpus testrun-vdeployment testrun-vdeployment-sample "$VDEPLOYMENT_SAMPLE_SIZE"
sample_corpus testrun-rabbitmq testrun-rabbitmq-sample "$RABBITMQ_SAMPLE_SIZE"

echo "=== Running fault injection against the sample (num-workers=$NUM_WORKERS) ==="

run_fi() {
    local config="$1" fi_config="$2" testrun_dir="$3" workdir="$4"
    rm -rf "$workdir"
    python3 -m chactos --config "$config" --fi-config "$fi_config" \
        --testrun-dir "$testrun_dir" --workdir "$workdir" --num-workers "$NUM_WORKERS"
}

ALL_WORKDIRS=()

for fic in vdeployment vreplicaset vdeployment-correlated vdeployment-pod-crash-rand; do
    wd="kick-the-tires-vdeployment-$fic"
    run_fi data/vdeployment-controller/v0/config.json "chactos/$fic.json" \
        testrun-vdeployment-sample "$wd"
    ALL_WORKDIRS+=("$wd")
done

for fic in rabbitmq-controller vstatefulset rabbitmq-controller-correlated rabbitmq-controller-pod-crash-rand; do
    wd="kick-the-tires-rabbitmq-$fic"
    run_fi data/anvil-rabbitmq-controller/config.json "chactos/$fic.json" \
        testrun-rabbitmq-sample "$wd"
    ALL_WORKDIRS+=("$wd")
done

echo "=== Summarizing results ==="
python3 welder-ae-correctness-summary.py "${ALL_WORKDIRS[@]}"
