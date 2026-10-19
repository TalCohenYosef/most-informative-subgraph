#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
TOY_DATA_ROOT=${TOY_DATA_ROOT:-"$PROJECT_DIR/data/generated/toy"}

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <RESULTS_ROOT> [--datasets color,pair,triangle] [--initial-threshold VALUE] [--threshold-step VALUE] [--max-attempts N] [--max-k K]" >&2
    echo "Defaults: --threshold-step 3 --max-k 8" >&2
    exit 1
fi

RESULTS_ROOT="$1"
shift
INITIAL_THRESHOLD="0"
THRESHOLD_STEP="3"
MAX_ATTEMPTS=50
MAX_K=8
DATASET_SELECTION="color,pair,triangle"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --datasets)
            DATASET_SELECTION="$2"
            shift 2
            ;;
        --initial-threshold)
            INITIAL_THRESHOLD="$2"
            shift 2
            ;;
        --threshold-step)
            THRESHOLD_STEP="$2"
            shift 2
            ;;
        --max-attempts)
            MAX_ATTEMPTS="$2"
            shift 2
            ;;
        --max-k)
            MAX_K="$2"
            shift 2
            ;;
        *)
            echo "Error: unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if ! [[ "$MAX_K" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --max-k must be a positive integer" >&2
    exit 1
fi

DATASET_DIRS=("unique_color" "unique_pair_graphs" "unique_tringle_graphs")
RESULT_NAMES=("unique_color" "unique_pair" "unique_triangle")

for index in "${!DATASET_DIRS[@]}"; do
    short_name=$(printf '%s' "${RESULT_NAMES[$index]}" | sed 's/^unique_//')
    if [[ ",$DATASET_SELECTION," != *",$short_name,"* ]]; then
        continue
    fi
    dataset_max_k="$MAX_K"
    if [[ "${RESULT_NAMES[$index]}" == "unique_color" ]]; then
        dataset_max_k=1
    fi
    for ((budget = 1; budget <= dataset_max_k; ++budget)); do
        threshold=$(awk -v initial="$INITIAL_THRESHOLD" -v k="$budget" 'BEGIN {print initial - 5 * (k - 1)}')
        result_dir="$RESULTS_ROOT/${RESULT_NAMES[$index]}/k_$budget"
        if [[ -f "$result_dir/summary.csv" ]] &&
           [[ $(awk 'END {print NR-1}' "$result_dir/summary.csv") -eq 1000 ]] &&
           [[ $(awk -F, -v k="$budget" 'NR > 1 && $3 != k {count++} END {print count+0}' "$result_dir/summary.csv") -eq 0 ]]; then
            echo "Skipping completed ${RESULT_NAMES[$index]} k=$budget"
            continue
        fi
        reuse_complete_run=0
        if [[ -f "$result_dir/summary.csv" ]] &&
           [[ $(awk 'END {print NR-1}' "$result_dir/summary.csv") -eq 1000 ]]; then
            reuse_complete_run=1
            threshold=$(awk -F= '$1 == "score_threshold" {print $2}' "$result_dir/run_config.txt")
            echo "Reusing completed ${RESULT_NAMES[$index]} k=$budget run; repairing mismatches only"
        fi
        calibrated=0
        calibration_dir="$RESULTS_ROOT/calibration/${RESULT_NAMES[$index]}/k_$budget"
        for ((attempt = 1; attempt <= MAX_ATTEMPTS && reuse_complete_run == 0; ++attempt)); do
            echo "Calibrating ${RESULT_NAMES[$index]} k=$budget on S_1, threshold=$threshold"
            set +e
            "$SCRIPT_DIR/run_toy_dataset_pipeline.sh" \
                "$TOY_DATA_ROOT/${DATASET_DIRS[$index]}" \
                "$calibration_dir" \
                --score-threshold "$threshold" \
                --required-pattern-size "$budget" \
                --s-name S_1
            calibration_exit=$?
            set -e
            if [[ "$calibration_exit" -eq 0 ]]; then
                calibrated=1
                break
            fi
            if [[ "$calibration_exit" -ne 2 ]]; then
                exit "$calibration_exit"
            fi

            measured_size=$(awk -F, 'NR == 2 {print $3+0}' "$calibration_dir/summary.csv")
            if [[ "$measured_size" -gt "$budget" ]]; then
                threshold=$(awk -v value="$threshold" -v step="$THRESHOLD_STEP" 'BEGIN {print value + step}')
            else
                threshold=$(awk -v value="$threshold" -v step="$THRESHOLD_STEP" 'BEGIN {print value - step}')
            fi
        done
        if [[ "$reuse_complete_run" -eq 0 && "$calibrated" -ne 1 ]]; then
            echo "Error: could not calibrate size k=$budget on S_1 for ${RESULT_NAMES[$index]}" >&2
            exit 2
        fi

        if [[ "$reuse_complete_run" -eq 0 ]]; then
            echo "Running all ${RESULT_NAMES[$index]} graphs at k=$budget with calibrated threshold=$threshold"
            set +e
            "$SCRIPT_DIR/run_toy_dataset_pipeline.sh" \
                "$TOY_DATA_ROOT/${DATASET_DIRS[$index]}" \
                "$result_dir" \
                --score-threshold "$threshold" \
                --required-pattern-size "$budget"
            full_run_exit=$?
            set -e
        else
            full_run_exit=2
        fi
        if [[ "$full_run_exit" -ne 0 && "$full_run_exit" -ne 2 ]]; then
            exit "$full_run_exit"
        fi

        if [[ "$full_run_exit" -eq 2 ]]; then
            mapfile -t mismatched_names < <(
                awk -F, -v k="$budget" 'NR > 1 && $3 != k {print $1}' "$result_dir/summary.csv"
            )
            echo "Repairing ${#mismatched_names[@]} patterns whose measured size is not k=$budget"
            for s_name in "${mismatched_names[@]}"; do
                s_threshold="$threshold"
                repaired=0
                repair_dir="$RESULTS_ROOT/repair/${RESULT_NAMES[$index]}/k_$budget/$s_name"
                for ((repair_attempt = 1; repair_attempt <= MAX_ATTEMPTS; ++repair_attempt)); do
                    measured_size=$(awk -F, -v name="$s_name" '$1 == name {print $3+0}' "$result_dir/summary.csv")
                    if [[ "$repair_attempt" -gt 1 ]]; then
                        measured_size=$(awk -F, 'NR == 2 {print $3+0}' "$repair_dir/summary.csv")
                    fi
                    if [[ "$measured_size" -gt "$budget" ]]; then
                        s_threshold=$(awk -v value="$s_threshold" -v step="$THRESHOLD_STEP" 'BEGIN {print value + step}')
                    else
                        s_threshold=$(awk -v value="$s_threshold" -v step="$THRESHOLD_STEP" 'BEGIN {print value - step}')
                    fi
                    echo "Repairing $s_name for k=$budget with threshold=$s_threshold"
                    set +e
                    "$SCRIPT_DIR/run_toy_dataset_pipeline.sh" \
                        "$TOY_DATA_ROOT/${DATASET_DIRS[$index]}" \
                        "$repair_dir" \
                        --score-threshold "$s_threshold" \
                        --required-pattern-size "$budget" \
                        --s-name "$s_name"
                    repair_exit=$?
                    set -e
                    if [[ "$repair_exit" -eq 0 ]]; then
                        repaired=1
                        break
                    fi
                    if [[ "$repair_exit" -ne 2 ]]; then
                        exit "$repair_exit"
                    fi
                done
                if [[ "$repaired" -ne 1 ]]; then
                    echo "Error: could not repair $s_name to size k=$budget" >&2
                    exit 2
                fi

                rm -rf "$result_dir/$s_name"
                cp -a "$repair_dir/$s_name" "$result_dir/$s_name"
                replacement_row=$(awk -F, 'NR == 2 {print}' "$repair_dir/summary.csv")
                awk -F, -v name="$s_name" -v replacement="$replacement_row" \
                    'BEGIN {OFS=FS} NR == 1 {print; next} $1 == name {print replacement; next} {print}' \
                    "$result_dir/summary.csv" > "$result_dir/summary.csv.tmp"
                mv "$result_dir/summary.csv.tmp" "$result_dir/summary.csv"
            done
        fi

        remaining_mismatches=$(awk -F, -v k="$budget" 'NR > 1 && $3 != k {count++} END {print count+0}' "$result_dir/summary.csv")
        if [[ "$remaining_mismatches" -ne 0 ]]; then
            echo "Error: $remaining_mismatches patterns still have size different from k=$budget" >&2
            exit 2
        fi
    done
done

if [[ -f "$RESULTS_ROOT/unique_color/k_1/summary.csv" ]] &&
   [[ -f "$RESULTS_ROOT/unique_pair/k_1/summary.csv" ]] &&
   [[ -f "$RESULTS_ROOT/unique_triangle/k_1/summary.csv" ]]; then
    python "$SCRIPT_DIR/plot_recovery_rate.py" \
        --results-dirs \
            "$RESULTS_ROOT/unique_color" \
            "$RESULTS_ROOT/unique_pair" \
            "$RESULTS_ROOT/unique_triangle" \
        --max-k "$MAX_K" \
        --output "$RESULTS_ROOT/recovery_rate.png"
    echo "Recovery plot: $RESULTS_ROOT/recovery_rate.png"
fi
