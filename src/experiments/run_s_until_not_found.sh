#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ -x "$SCRIPT_DIR/run_toy_dataset_pipeline.sh" ]]; then
    PIPELINE="$SCRIPT_DIR/run_toy_dataset_pipeline.sh"
else
    echo "Error: cannot find run_toy_dataset_pipeline.sh" >&2
    exit 1
fi

if [[ $# -lt 3 ]]; then
    echo "Usage: $0 <S_INPUT_DIR> <G.json> <RESULTS_DIR> [--initial-threshold VALUE] [--threshold-step VALUE] [--max-size K] [--max-attempts N] [--jobs N] [--threads-per-job N]" >&2
    exit 1
fi

S_INPUT_DIR=$1
G_PATH=$2
RESULTS_ROOT=$3
shift 3

INITIAL_THRESHOLD=0
THRESHOLD_STEP=3
MAX_SIZE=100
MAX_ATTEMPTS=50
JOBS=$(nproc 2>/dev/null || echo 4)
THREADS_PER_JOB=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --initial-threshold) INITIAL_THRESHOLD=$2; shift 2 ;;
        --threshold-step) THRESHOLD_STEP=$2; shift 2 ;;
        --max-size) MAX_SIZE=$2; shift 2 ;;
        --max-attempts) MAX_ATTEMPTS=$2; shift 2 ;;
        --jobs) JOBS=$2; shift 2 ;;
        --threads-per-job) THREADS_PER_JOB=$2; shift 2 ;;
        *) echo "Error: unknown option: $1" >&2; exit 1 ;;
    esac
done

[[ -d "$S_INPUT_DIR" ]] || { echo "Error: missing S input directory: $S_INPUT_DIR" >&2; exit 1; }
[[ -f "$G_PATH" ]] || { echo "Error: missing G.json: $G_PATH" >&2; exit 1; }
# Worker datasets live under /tmp, so symlink targets must be absolute.
S_INPUT_DIR=$(realpath "$S_INPUT_DIR")
G_PATH=$(realpath "$G_PATH")
[[ "$MAX_SIZE" =~ ^[1-9][0-9]*$ ]] || { echo "Error: --max-size must be positive" >&2; exit 1; }
[[ "$MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ ]] || { echo "Error: --max-attempts must be positive" >&2; exit 1; }
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo "Error: --jobs must be positive" >&2; exit 1; }
[[ "$THREADS_PER_JOB" =~ ^[1-9][0-9]*$ ]] || { echo "Error: --threads-per-job must be positive" >&2; exit 1; }

mkdir -p "$RESULTS_ROOT"
RESULTS_ROOT=$(realpath "$RESULTS_ROOT")
SUMMARY="$RESULTS_ROOT/first_not_found.csv"
TIMING_SUMMARY="$RESULTS_ROOT/first_not_found_timings.csv"

TMP_SUMMARY_DIR=$(mktemp -d /tmp/sgf_until_not_found_summary.XXXXXX)
cleanup() { rm -rf "$TMP_SUMMARY_DIR"; }
trap cleanup EXIT

mapfile -t S_FILES < <(
    for path in "$S_INPUT_DIR"/S_*.json; do
        [[ -f "$path" ]] || continue
        name=$(basename "$path" .json)
        [[ "$name" =~ ^S_[0-9]+$ ]] || continue
        printf '%05d\t%s\n' "${name#S_}" "$path"
    done | sort -k1,1n | cut -f2-
)
[[ ${#S_FILES[@]} -gt 0 ]] || { echo "Error: no S_*.json files found in $S_INPUT_DIR" >&2; exit 1; }

process_one_s() {
    trap - EXIT
    local s_path=$1
    local s_name
    local s_dir
    local threshold
    local k
    local attempt
    local run_dir
    local row
    local measured
    local status
    local calibrated
    local stopped
    local previous_run_dir
    local previous_threshold
    local previous_status
    local current_status
    local current_measured
    local worker_dataset
    local timing_row

    s_name=$(basename "$s_path" .json)
    s_dir="$RESULTS_ROOT/$s_name"
    mkdir -p "$s_dir"
    worker_dataset=$(mktemp -d /tmp/sgf_until_not_found_worker.XXXXXX)
    ln -s "$G_PATH" "$worker_dataset/G.json"
    ln -s "$s_path" "$worker_dataset/$s_name.json"
    threshold=$INITIAL_THRESHOLD
    stopped=0

    for ((k=1; k<=MAX_SIZE; k++)); do
        run_dir="$s_dir/k_$k"
        if [[ -f "$run_dir/summary.csv" ]]; then
            current_measured=$(awk -F, 'NR == 2 {print $3}' "$run_dir/summary.csv")
            current_status=$(awk -F, 'NR == 2 {print $4}' "$run_dir/summary.csv")
            if [[ "$current_measured" == "$k" && "$current_status" == "not_found" ]]; then
                printf '%s,%s,not_found\n' "$s_name" "$k" > "$TMP_SUMMARY_DIR/${s_name}.csv"
                if [[ -s "$run_dir/timings.csv" ]]; then
                    timing_row=$(awk -F, 'NR == 2 {print $2 "," $3 "," $4 "," $5}' "$run_dir/timings.csv")
                    printf '%s,%s,%s,not_found\n' "$s_name" "$k" "$timing_row" > "$TMP_SUMMARY_DIR/${s_name}.timing"
                fi
                stopped=1
                break
            fi
            if [[ "$current_measured" == "$k" && "$current_status" == "found" ]]; then
                echo "$s_name: k=$k already complete"
                continue
            fi
        fi
        previous_run_dir="$s_dir/k_$((k - 1))"
        if (( k > 1 )) && [[ -f "$previous_run_dir/summary.csv" ]]; then
            previous_status=$(awk -F, 'NR == 2 {print $4}' "$previous_run_dir/summary.csv")
            if [[ "$previous_status" == "not_found" ]]; then
                stopped=1
                break
            fi
            previous_threshold=$(awk -F= '$1 == "score_threshold" {print $2}' "$previous_run_dir/run_config.txt" 2>/dev/null || true)
            if [[ "$previous_threshold" =~ ^-?[0-9]+([.][0-9]+)?$ ]]; then
                threshold=$previous_threshold
            fi
        fi
        calibrated=0
        for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
            set +e
            "$PIPELINE" "$worker_dataset" "$run_dir" \
                --score-threshold "$threshold" \
                --required-pattern-size "$k" \
                --thread-number "$THREADS_PER_JOB" \
                --s-name "$s_name" >/dev/null
            exit_code=$?
            set -e

            if [[ ! -f "$run_dir/summary.csv" ]] ||
               [[ $(awk -F, 'NR == 2 {print $4}' "$run_dir/summary.csv") == "error" ]]; then
                echo "Error: pipeline failed for $s_name at k=$k (exit=$exit_code)" >&2
                printf '%s,,error\n' "$s_name" > "$TMP_SUMMARY_DIR/${s_name}.csv"
                rm -rf "$worker_dataset"
                return 0
            fi
            rm -f "$run_dir/summary.txt"

            row=$(awk -F, 'NR == 2 {print}' "$run_dir/summary.csv")
            measured=$(printf '%s\n' "$row" | awk -F, '{print $3}')
            status=$(printf '%s\n' "$row" | awk -F, '{print $4}')

            if [[ "$measured" == "$k" ]]; then
                calibrated=1
                if [[ "$status" == "found" ]]; then
                    echo "$s_name: k=$k found (threshold=$threshold)"
                else
                    echo "$s_name: k=$k not found; stopping"
                    printf '%s,%s,not_found\n' "$s_name" "$k" > "$TMP_SUMMARY_DIR/${s_name}.csv"
                    timing_row=$(awk -F, 'NR == 2 {print $2 "," $3 "," $4 "," $5}' "$run_dir/timings.csv")
                    printf '%s,%s,%s,not_found\n' "$s_name" "$k" "$timing_row" > "$TMP_SUMMARY_DIR/${s_name}.timing"
                    stopped=1
                fi
                break
            fi

            if [[ "$measured" =~ ^[0-9]+$ ]] && (( measured > k )); then
                threshold=$(awk -v v="$threshold" -v d="$THRESHOLD_STEP" 'BEGIN {print v+d}')
            else
                threshold=$(awk -v v="$threshold" -v d="$THRESHOLD_STEP" 'BEGIN {print v-d}')
            fi
        done

        if [[ "$calibrated" -ne 1 ]]; then
            echo "Error: could not calibrate $s_name to size $k" >&2
            printf '%s,%s,error\n' "$s_name" "$k" > "$TMP_SUMMARY_DIR/${s_name}.csv"
            rm -rf "$worker_dataset"
            return 0
        fi
        [[ "$stopped" -eq 1 ]] && break
    done

    if [[ "$stopped" -eq 0 ]]; then
        printf '%s,,max_size_reached\n' "$s_name" > "$TMP_SUMMARY_DIR/${s_name}.csv"
    fi
    rm -rf "$worker_dataset"
}

running=0
pids=()
for s_path in "${S_FILES[@]}"; do
    process_one_s "$s_path" &
    pids+=("$!")
    running=$((running + 1))

    if (( running >= JOBS )); then
        wait -n
        running=$((running - 1))
    fi
done

for pid in "${pids[@]}"; do
    wait "$pid"

done

{
    echo "S_NAME,first_not_found_size,status"
    for partial in "$TMP_SUMMARY_DIR"/*.csv; do
        [[ -f "$partial" ]] || continue
        cat "$partial"
    done
} > "$SUMMARY"

{
    echo "S_NAME,first_not_found_size,pattern_generation_seconds,graph_search_seconds,total_seconds,patterns_searched,status"
    for partial in "$TMP_SUMMARY_DIR"/*.timing; do
        [[ -f "$partial" ]] || continue
        cat "$partial"
    done
} > "$TIMING_SUMMARY"

echo "Summary CSV: $SUMMARY"
echo "First-not-found timing CSV: $TIMING_SUMMARY"
