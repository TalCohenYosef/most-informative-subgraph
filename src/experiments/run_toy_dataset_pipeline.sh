#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# Usage:
#   ./run_dataset_pipeline.sh <DATASET_DIR> <RESULTS_DIR> [options]
#
# Options:
#   --score-threshold VALUE   Pattern Finder score cutoff (default: -15)
#   --required-pattern-size K Require the selected pattern to have exactly K vertices
#   --thread-number N         Threads used by the pattern finder (default: 1)
#   --s-name S_NAME           Process one graph only (for example S_1)
#
# ============================================================

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <DATASET_DIR> <RESULTS_DIR> [--score-threshold VALUE] [--required-pattern-size K] [--thread-number N] [--s-name S_NAME]"
    exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

SGF_BUILD_DIR=${SGF_BUILD_DIR:-"$PROJECT_DIR/.external/subgraph_filter_suit/build"}
PATTERN_FINDER="$SGF_BUILD_DIR/sgf-pattern-finder"
GRAPH_SEARCHER="$SGF_BUILD_DIR/sgf-graph-searcher"

DATASET_DIR="$1"
RESULTS_DIR="$2"
shift 2

SCORE_THRESHOLD="-15"
REQUIRED_PATTERN_SIZE=""
THREAD_NUMBER=1
ONLY_S_NAME=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --score-threshold)
            [[ $# -ge 2 ]] || { echo "Error: --score-threshold needs a value" >&2; exit 1; }
            SCORE_THRESHOLD="$2"
            shift 2
            ;;
        --required-pattern-size)
            [[ $# -ge 2 ]] || { echo "Error: --required-pattern-size needs a value" >&2; exit 1; }
            REQUIRED_PATTERN_SIZE="$2"
            shift 2
            ;;
        --thread-number)
            [[ $# -ge 2 ]] || { echo "Error: --thread-number needs a value" >&2; exit 1; }
            THREAD_NUMBER="$2"
            shift 2
            ;;
        --s-name)
            [[ $# -ge 2 ]] || { echo "Error: --s-name needs a value" >&2; exit 1; }
            ONLY_S_NAME="$2"
            shift 2
            ;;
        *)
            echo "Error: unknown option: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -n "$REQUIRED_PATTERN_SIZE" ]] && ! [[ "$REQUIRED_PATTERN_SIZE" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --required-pattern-size must be a positive integer" >&2
    exit 1
fi
if ! [[ "$THREAD_NUMBER" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --thread-number must be a positive integer" >&2
    exit 1
fi

shopt -s nullglob

if [[ -d "$DATASET_DIR/S_graphs" ]]; then
    G_PATH="$DATASET_DIR/G.json"
    S_DIR="$DATASET_DIR/S_graphs"
elif [[ -f "$DATASET_DIR/G.json" ]]; then
    G_PATH="$DATASET_DIR/G.json"
    S_DIR="$DATASET_DIR"
else
    echo "Error: expected a dataset directory containing G.json and S_graphs/, or a directory containing G.json and S_*.json" >&2
    exit 1
fi

if [[ ! -f "$G_PATH" ]]; then
    echo "Error: missing G.json at $G_PATH" >&2
    exit 1
fi

if [[ ! -d "$S_DIR" ]]; then
    echo "Error: missing graph directory at $S_DIR" >&2
    exit 1
fi

S_FILES=("$S_DIR"/S_*.json)
if [[ ${#S_FILES[@]} -eq 0 ]]; then
    echo "Error: no S_*.json files found in $S_DIR" >&2
    exit 1
fi

TMP_LIBRARY=$(mktemp -d /tmp/sgf_figure1_library.XXXXXX)
cleanup_tmp_library() {
    rm -rf "$TMP_LIBRARY"
}
trap cleanup_tmp_library EXIT

READER_TYPE="json"
PATTERN_OUTPUT_TYPE="json"
PRIOR_POLICY="combined"

mkdir -p "$RESULTS_DIR"

SUMMARY_CSV="$RESULTS_DIR/summary.csv"
TMP_SUMMARY="$RESULTS_DIR/summary.tmp"
SUMMARY_TXT="$RESULTS_DIR/summary.txt"
TIMINGS_CSV="$RESULTS_DIR/timings.csv"

echo "S_NAME,best_matches,pattern_size,status" > "$SUMMARY_CSV"
echo "S_NAME,pattern_generation_seconds,graph_search_seconds,total_seconds,patterns_searched" > "$TIMINGS_CSV"
{
    echo "Not found in G: pending"
    echo "Graphs with no match in G: pending"
    echo
    echo "S graphs with matches > 0:"
} > "$SUMMARY_TXT"

# Keep a count of how many S graphs are not found in G.
NOT_FOUND_COUNT=0

count=0

mapfile -t S_FILES < <(
    for path in "$S_DIR"/S_*.json; do
        [[ -f "$path" ]] || continue
        base=$(basename "$path" .json)
        [[ "$base" =~ ^S_[0-9]+$ ]] || continue
        num=${base#S_}
        printf '%05d\t%s\n' "$num" "$path"
    done | sort -k1,1n | cut -f2-
)
for S_PATH in "${S_FILES[@]}"
do
    if [[ ! -f "$S_PATH" ]]; then
        continue
    fi

    S_NAME=$(basename "$S_PATH" .json)
    if [[ -n "$ONLY_S_NAME" && "$S_NAME" != "$ONLY_S_NAME" ]]; then
        continue
    fi
    OUT_DIR="$RESULTS_DIR/$S_NAME"

    echo "========================================"
    echo "Processing $S_NAME"
    echo "========================================"

    rm -rf "$OUT_DIR"
    mkdir -p "$OUT_DIR"

    cp "$S_PATH" "$TMP_LIBRARY/"

    # --------------------------------------------------------
    # Step 1: pattern finder
    # --------------------------------------------------------
    PIPELINE_START_NS=$(date +%s%N)
    FINDER_START_NS=$PIPELINE_START_NS
    set +e
    "$PATTERN_FINDER" \
        --preprocess \
        --reader-type "$READER_TYPE" \
        --library-input-folder "$TMP_LIBRARY" \
        --output-folder "$OUT_DIR" \
        --pattern-output-type "$PATTERN_OUTPUT_TYPE" \
        --preprocess-single-graph 0 \
        --background-graph-path "$G_PATH" \
        --score-threshold "$SCORE_THRESHOLD" \
        --thread-number "$THREAD_NUMBER" \
        > "$OUT_DIR/pattern_finder.log" 2>&1
    FINDER_EXIT=$?
    set -e
    FINDER_END_NS=$(date +%s%N)

    S_MATCHED=0
    BEST_MATCHES=""
    BEST_PATTERN=""
    BEST_PATTERN_SIZE=""
    PATTERNS_SEARCHED=0
    SEARCH_START_NS=$(date +%s%N)

    if [[ $FINDER_EXIT -eq 0 ]]; then
        PATTERN_FILES=("$OUT_DIR"/pattern_*.json)

        if [[ ${#PATTERN_FILES[@]} -gt 0 ]]; then
            for PATTERN_FILE in "${PATTERN_FILES[@]}"; do
                if [[ ! -f "$PATTERN_FILE" ]]; then
                    continue
                fi
                PATTERNS_SEARCHED=$((PATTERNS_SEARCHED + 1))

                PATTERN_SIZE=$(python -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["nodes"]))' "$PATTERN_FILE")
                set +e
                SEARCH_OUTPUT=$("$GRAPH_SEARCHER" \
                    --subgraph-path "$PATTERN_FILE" \
                    --background-path "$G_PATH" \
                    --reader-type "$READER_TYPE" \
                    --prior-policy "$PRIOR_POLICY" \
                    --stop-on-first-match 2>&1)
                SEARCH_EXIT=$?
                set -e
                if [[ $SEARCH_EXIT -eq 0 && "$SEARCH_OUTPUT" =~ Matches[[:space:]]found:[[:space:]]*([0-9]+) ]]; then
                    MATCHES_FOUND="${BASH_REMATCH[1]}"
                    if [[ -z "$BEST_MATCHES" || "$MATCHES_FOUND" -lt "$BEST_MATCHES" || ( "$MATCHES_FOUND" -eq "$BEST_MATCHES" && "$PATTERN_SIZE" -lt "$BEST_PATTERN_SIZE" ) ]]; then
                        BEST_MATCHES="$MATCHES_FOUND"
                        BEST_PATTERN="$PATTERN_FILE"
                        BEST_PATTERN_SIZE="$PATTERN_SIZE"
                    fi
                fi
            done
        fi
    fi
    SEARCH_END_NS=$(date +%s%N)
    PIPELINE_END_NS=$SEARCH_END_NS

    PATTERN_GENERATION_SECONDS=$(awk -v start="$FINDER_START_NS" -v end="$FINDER_END_NS" 'BEGIN {printf "%.6f", (end-start)/1000000000}')
    GRAPH_SEARCH_SECONDS=$(awk -v start="$SEARCH_START_NS" -v end="$SEARCH_END_NS" 'BEGIN {printf "%.6f", (end-start)/1000000000}')
    TOTAL_SECONDS=$(awk -v start="$PIPELINE_START_NS" -v end="$PIPELINE_END_NS" 'BEGIN {printf "%.6f", (end-start)/1000000000}')
    printf '%s,%s,%s,%s,%s\n' \
        "$S_NAME" "$PATTERN_GENERATION_SECONDS" "$GRAPH_SEARCH_SECONDS" \
        "$TOTAL_SECONDS" "$PATTERNS_SEARCHED" >> "$TIMINGS_CSV"
    {
        echo "pattern_generation_seconds=$PATTERN_GENERATION_SECONDS"
        echo "graph_search_seconds=$GRAPH_SEARCH_SECONDS"
        echo "total_seconds=$TOTAL_SECONDS"
        echo "patterns_searched=$PATTERNS_SEARCHED"
    } > "$OUT_DIR/timing.txt"

    if [[ -n "$BEST_PATTERN" ]]; then
        cp "$BEST_PATTERN" "$OUT_DIR/best_pattern.json"
        echo "$BEST_MATCHES" > "$OUT_DIR/best_match_count.txt"
        echo "$BEST_PATTERN_SIZE" > "$OUT_DIR/best_pattern_size.txt"
        if [[ "$BEST_MATCHES" -gt 0 ]]; then
            S_MATCHED=1
        fi
    fi

    # Keep all generated patterns so they can be inspected after the run.

    if [[ $S_MATCHED -eq 0 ]]; then
        NOT_FOUND_COUNT=$((NOT_FOUND_COUNT + 1))
        if [[ -n "$BEST_MATCHES" ]]; then
            echo "$S_NAME,$BEST_MATCHES,$BEST_PATTERN_SIZE,not_found" >> "$SUMMARY_CSV"
        else
            echo "$S_NAME,,,error" >> "$SUMMARY_CSV"
        fi
    else
        echo "$S_NAME,$BEST_MATCHES,$BEST_PATTERN_SIZE,found" >> "$SUMMARY_CSV"
        echo "$S_NAME: $BEST_MATCHES matches" >> "$SUMMARY_TXT"
    fi

    # Keep only the selected pattern and its compact metadata for this S_i.
    rm -f "$OUT_DIR"/pattern_*.json "$OUT_DIR"/pattern_index_*.csv
    rm -f "$TMP_LIBRARY"/*.json

    count=$((count + 1))

    if (( count % 50 == 0 )); then
        echo "Completed $count graphs"
    fi
done

echo
printf 'Not found in G: %d\n' "$NOT_FOUND_COUNT"
echo "Finished."
echo "Graphs with no match in G: $NOT_FOUND_COUNT"

TOTAL_GRAPHS=$count
FOUND_COUNT=$((TOTAL_GRAPHS - NOT_FOUND_COUNT))
{
    echo "Not found in G: $NOT_FOUND_COUNT"
    echo "Finished."
    echo "Graphs with no match in G: $NOT_FOUND_COUNT"
    echo "Graphs with matches > 0: $FOUND_COUNT"
    echo
    echo "S graphs with matches > 0:"
    awk -F, 'NR > 1 && $4 == "found" { print $1 ": " $2 " matches" }' "$SUMMARY_CSV"
} > "$SUMMARY_TXT"

{
    echo "score_threshold=$SCORE_THRESHOLD"
    echo "required_pattern_size=$REQUIRED_PATTERN_SIZE"
    echo "thread_number=$THREAD_NUMBER"
    echo "total_graphs=$TOTAL_GRAPHS"
} > "$RESULTS_DIR/run_config.txt"

echo "Summary CSV: $SUMMARY_CSV"
echo "Summary text: $SUMMARY_TXT"

if [[ -n "$REQUIRED_PATTERN_SIZE" ]]; then
    SIZE_MISMATCHES=$(awk -F, -v k="$REQUIRED_PATTERN_SIZE" 'NR > 1 && $3 != k {count++} END {print count+0}' "$SUMMARY_CSV")
    echo "Patterns with size different from k=$REQUIRED_PATTERN_SIZE: $SIZE_MISMATCHES"
    if [[ "$SIZE_MISMATCHES" -gt 0 ]]; then
        exit 2
    fi
fi
