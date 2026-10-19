# Experiment commands and parameters

These commands document the original workflow. They have not yet been tested
from a clean checkout. Set `SGF_BUILD_DIR` to the `build/` directory of Subgraph
Filter Suite commit `b4a90b08a2d418b137f06edd09044da400b567d8` and replace
machine-specific paths with a local benchmark directory. The original GNP
payload used for the saved results is not distributed. A newly generated
replacement can exercise the workflow, but it will not reproduce the saved
numerical summaries exactly.

## VISTA per-query benchmark

The preserved driver is `src/experiments/run_s_until_not_found.sh` and calls
the pattern preprocessing/search pipeline for increasing pattern sizes. The
saved experiment used one search thread per query. Per-budget score thresholds
were calibrated dynamically and were stored in the original detailed run
directories; the compact repository preserves the final outcome and timing
summaries used by the figures.

## Graphlets Enumeration

Graphlets results were produced with `sgf-graph-enumerator` in motif mode using
colored four-graphlet caches. The compact package contains all 144 final
filter-result CSVs and timing summaries, but not the 82 GB enumeration caches.
The result encoding is `1 = negated/rejected`, `0 = survived`.

## VISTA+

The preserved campaign runner is:

```bash
SGF_BUILD_DIR=/path/to/subgraph_filter_suit/build \
GNP_BENCHMARK_ROOT=/path/to/generated/gnp \
bash src/experiments/run_vista_plus_300.sh
```

The output defaults to `data/results/vista_plus_new` so the archived summaries
in `data/results/vista_plus` are never overwritten.
The exact saved parameters are in `configs/vista_plus.yml` and in each run's
`run_config.json`:

- 1,000 queries in each of 12 query configurations
- 12 reference graphs per query configuration
- support fraction 0.03 (minimum support 30)
- 300 patterns requested
- miner batch size 3 and two miner threads
- maximum pattern size 20 for degrees 3/5 and 15 for degrees 8/15
- preprocessing timeout 10,800 seconds
- search timeout 120 seconds
- miner/search memory limits 160/24 GiB

Figure 6 regeneration uses only saved summaries and does not require recovered
pattern JSON files.
