# Initial migration validation

Validation was performed without running expensive experiments and without
overwriting any saved output. Regenerated plots were written to a temporary
directory.

## File counts

- Original GNP provenance manifest: 12 reference graphs and 12,000 numbered
  query graphs (the payload itself is not distributed)
- VISTA compact synthetic summaries: 144
- VISTA case summaries: 144
- VISTA timing summaries: 144
- Graphlets filtering summaries: 144
- Real-world result sets: 3, each with 100 query rows
- VISTA+ runs: 12
- VISTA+ reference summaries: 144
- Toy data files: 3,009

## Reader validation

- Figure 2 loaded all three toy cases and the documented fallback recovery values.
- Figure 3 loaded all 144 VISTA and Graphlets configurations and three real-world
  curves. Its Graphlets matrix contains 21.5% and 0.2% under the maximum rule.
- Figure 4 built all 144 matched comparison series.
- Figure 5 loaded twelve VISTA timing families, twelve Graphlets timing families,
  and a 10×10 theory-score heatmap containing 1,440 observations.
- Figure 6 discovered twelve VISTA+ runs, a complete 12×12 matrix, and twelve
  membership distributions.

## Non-overwriting plot comparison

The following regenerated PNGs were byte-identical to the saved final PNGs:

- Figure 2: `5b07bc94e25b9787af60f3c5759e0d5661c14dfcfbc0b6da99032717c52cae62`
- Figure 4: `7fb31d09cc3143ce0f03a3080e92aed7e4895df667456be26ed89ddf898918c2`
- Figure 5: `dae1bbdb7b1862cbfad22ed19cb10f80c22aa2ff7f1362739a3777515707a3db`
- Figure 6: `f839b28fb84b7f6911fa9d24cf1a12c65a8ce7227718ae7497bb0e8065731c88`

Figure 5's regenerated `case_timings_aggregated.csv` was also byte-identical.

Figure 3's reconstructed script executes successfully and reproduces the
underlying numerical panels, but its layout is not byte- or pixel-identical to
the saved composite. It remains pending layout validation.
