# Migration source map

All sources below were copied; the original experiment directory was not
modified.

| Migrated destination | Original source |
|---|---|
| `data/generated/toy_models/` | `locL_test/figure1_toy_models/{unique_color,unique_pair_graphs,unique_tringle_graphs}` |
| `data/results/vista/synthetic_summaries/` | `locL_test/pattern_finder_summaries_for_plots_20260922/` |
| `data/results/vista/case_summaries/` | 144 `first_not_found.csv` files under `locL_test/recovery_results_pattern_finder/` |
| `data/results/vista/timings/` | 144 `first_not_found_timings.csv` files under the same tree |
| `data/results/graphlets/filter_results/` | `locL_test/recovery_results_motifs/Gnp_motifs/timing_1000_queries/filter_results/` |
| `data/results/graphlets/timings/` | Graphlets timing CSVs in `timing_1000_queries/` |
| `data/results/theory/detailed_configuration_results.csv` | `gnp_vista_lambda_analysis_20260924/theory_results_package/advisor_theory_results_package/` |
| `data/results/realworld/` | final BookChild, SportsFit and ogbn-arxiv `*_random_frontier` summaries and original-label recovery results |
| `data/results/vista_plus/` | compact files from `multiple_tests/.../experiment_alive_0p03_patterns_300/input_color_*` |
| `figures/figure_02/` … `figures/figure_06/` | final manuscript PNGs and plotting code from `locL_test/` and `multiple_tests/` |

Copied plotting and experiment scripts retain their scientific calculations.
Only path/import defaults in the copies were adjusted for the new repository.
