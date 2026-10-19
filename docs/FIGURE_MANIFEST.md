# Figure manifest

## Figure 1

Manual conceptual schematic. No computational script is required.

## Figure 2 — Toy models and planted-structure recovery

- Script: `figures/figure_02/plot.py`
- Inputs: `data/generated/toy_models/{unique_color,unique_pair,unique_triangle}/`
- Output: `figures/figure_02/figure_02.png`
- Clean-environment validation: regenerated PNG has identical dimensions and
  pixel values. Its encoded-file hash differs because the saved image records
  Matplotlib 3.7.1 while the clean environment resolves Matplotlib 3.7.3.
- Status: plot reproducible; recovery values remain hard-coded and unverified.

## Figure 3 — Synthetic, Graphlets and real-world negation

- Script: `figures/figure_03/plot.py`
- Supporting VISTA panel: `figures/analysis/figure_03_vista_panel.py`
- VISTA input: `data/results/vista/synthetic_summaries/*.csv` (144 files)
- Graphlets input: `data/results/graphlets/filter_results/**/*.csv` (144 files)
- Real-world inputs: `data/results/realworld/*/recovery_results/first_not_found.csv`
- Output: `figures/figure_03/figure_03.png`
- Calculation: each Graphlets degree cell is the maximum survival percentage
  across the nine query/reference color-distribution pairs.
- Clean-environment validation: all numerical panels regenerate, including the
  21.5% and 0.2% Graphlets cells. The reconstructed composite is not visually
  identical to the saved paper figure because of the layout differences
  documented in `REPRODUCIBILITY.md`.
- Status: plot reproducible numerically; final layout remains unresolved.

## Figure 4 — VISTA versus Graphlets Enumeration

- Script: `figures/figure_04/plot.py`
- Shared reader: `figures/analysis/result_readers.py`
- Inputs: 144 Graphlets filtering CSVs and 144 VISTA `first_not_found.csv` files
- Output: `figures/figure_04/figure_04.png`
- Clean-environment validation: regenerated PNG has identical dimensions and
  pixel values; its encoded-file hash differs by Matplotlib metadata.
- Status: plot reproducible from saved results.

## Figure 5 — Score, negation and computational cost

- Script: `figures/figure_05/plot.py`
- Inputs: `data/results/graphlets/timings/*.csv`, 144 VISTA timing summaries,
  and `data/results/theory/detailed_configuration_results.csv`
- Derived table: `data/results/theory/case_timings_aggregated.csv`
- Output: `figures/figure_05/figure_05.png`
- Clean-environment validation: regenerated PNG has identical dimensions and
  pixel values, and the derived aggregate CSV is byte-identical. Encoded image
  hashes differ by Matplotlib metadata.
- Status: plot reproducible from saved results.

## Figure 6 — VISTA+

- Script: `figures/figure_06/plot.py`
- Supporting modules: `figures/analysis/figure_06_matrix.py`,
  `figures/analysis/figure_06_membership.py`
- Inputs: `data/results/vista_plus/input_color_*`, specifically each run's
  `run_config.json`, `pattern_to_S_indices.json`, `timings.json`,
  `G_summary.txt`, and twelve `G_*/summary.json` files
- Output: `figures/figure_06/figure_06.png`
- Clean-environment validation: regenerated PNG has identical dimensions and
  pixel values; its encoded-file hash differs by Matplotlib metadata.
- Status: plot reproducible from saved results.
