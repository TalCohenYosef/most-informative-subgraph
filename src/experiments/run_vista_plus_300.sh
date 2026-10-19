#!/usr/bin/env bash

set -u

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repository_root=$(cd "$script_dir/../.." && pwd)
benchmark_root=${GNP_BENCHMARK_ROOT:-"$repository_root/data/generated/gnp/files"}
output_root=${VISTA_PLUS_OUTPUT_ROOT:-"$repository_root/data/results/vista_plus_new"}
runner="$script_dir/run_multigraph_evidence.py"

datasets=(
  input_color_average_deg_3
  input_color_average_deg_5
  input_color_average_deg_8
  input_color_average_deg_15
  input_color_rare_deg_3
  input_color_rare_deg_5
  input_color_rare_deg_8
  input_color_rare_deg_15
  input_color_uniform_deg_3
  input_color_uniform_deg_5
  input_color_uniform_deg_8
  input_color_uniform_deg_15
)

mkdir -p "$output_root"

printf '[%s] Campaign started\n' "$(date '+%Y-%m-%d %H:%M:%S')"
printf 'Output root: %s\n' "$output_root"
printf 'Datasets: %s; patterns per dataset: 300; alive fraction: 0.03\n' "${#datasets[@]}"
printf 'Checkpoint interval: 3 patterns; miner memory cap: 160 GiB\n'

overall_status=0
for dataset in "${datasets[@]}"; do
  degree="${dataset##*_deg_}"
  if [[ "$degree" == 8 || "$degree" == 15 ]]; then
    max_pattern_vertices=15
  else
    max_pattern_vertices=20
  fi

  printf '[%s] Starting %s (K=%s)\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$dataset" "$max_pattern_vertices"

  if python3 -u "$runner" \
      --input-dir "$benchmark_root/$dataset" \
      --graph-dir "$benchmark_root/graphs_deg_5" \
      --output-root "$output_root" \
      --alive-percent 0.03 \
      --patterns 300 \
      --max-pattern-vertices "$max_pattern_vertices" \
      --threads 2 \
      --miner-batch-size 3 \
      --preprocess-timeout 10800 \
      --search-timeout 120 \
      --miner-memory-gb 160 \
      --search-memory-gb 24; then
    printf '[%s] Completed %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$dataset"
  else
    status=$?
    overall_status=1
    printf '[%s] FAILED %s (exit %s); continuing to next dataset\n' \
      "$(date '+%Y-%m-%d %H:%M:%S')" "$dataset" "$status"
  fi
done

printf '[%s] Campaign finished with status %s\n' \
  "$(date '+%Y-%m-%d %H:%M:%S')" "$overall_status"
exit "$overall_status"
