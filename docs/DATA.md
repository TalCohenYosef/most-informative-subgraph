# Data inventory

## Toy benchmarks

`data/generated/toy_models/` contains the three Figure 2 benchmarks, including each
reference graph, 1,000 query graphs, and planted-structure ground truth. The
original misspelling `unique_tringle_graphs` is retained to avoid silently
changing paths or provenance.

## Synthetic GNP benchmark

The approximately 5.3 GB original GNP graph payload is not distributed.
`data/generation_code/gnp/generate_gnp_benchmark.py` generates a reproducible
replacement with the manuscript's twelve color/degree configurations, legacy
filenames, and JSON schema. The precise original connectivity-repair rule and
random seed were not preserved, so generated graphs are not the graph instances
underlying the saved paper results. Assumptions and commands are documented in
`data/generation_code/gnp/README.md`.

`data/generated/gnp/BENCHMARK_MANIFEST.csv` remains as a provenance record for
the unpublished originals. Its checksums do not apply to replacement graphs.
Generated GNP payloads under `data/generated/gnp/references/` and `queries/` are
excluded from ordinary Git.

## Real-world benchmarks

`data/generated/realworld/` contains the final extracted reference graphs,
numbered query graphs, and extraction summaries for BookChild, SportsFit, and
ogbn-arxiv. The extraction implementation is included at
`data/generation_code/realworld/extract_disjoint_color_graphs_random_frontier.py`.

The original source files under `data/raw/realworld/` are present only in the
local preparation workspace and are excluded from Git because of size and
redistribution/provenance constraints. Reviewers can inspect and use the final
extracted graphs, but cannot rerun extraction from the original source inputs
from a GitHub clone alone unless those inputs are separately obtained.

## Saved results

- `data/results/vista/synthetic_summaries/`: 144 VISTA survival summaries.
- `data/results/vista/case_summaries/`: 144 per-configuration VISTA summaries.
- `data/results/vista/timings/`: 144 VISTA timing summaries.
- `data/results/graphlets/filter_results/`: 144 Graphlets filtering outcomes,
  organized as `query_<family>_deg_<n>/background_<family>_deg_<n>/`.
- `data/results/graphlets/timings/`: preprocessing and per-case timing tables.
- `data/results/theory/`: score data and aggregated timing reference table.
- `data/results/realworld/`: final original-label recovery summaries and graph
  statistics for BookChild, SportsFit, and ogbn-arxiv.
- `data/results/vista_plus/`: compact final summaries from the twelve Figure 6
  runs. Pattern JSON files and miner intermediates are outside the agreed scope.

The randomized-color real-world experiments, motif caches, path experiments,
candidate analyses, checkpoints, and historical runs are not part of the paper
result package.

Some saved CSV/JSON result rows retain absolute source paths as immutable
provenance fields. Plotting code uses only their basenames or numerical fields;
the paths are not runtime dependencies and were not rewritten.
