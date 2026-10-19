# Clean-environment validation

Validation date: 2026-10-18. All commands were run inside this repository.
Generated artifacts were written below the Git-ignored `.validation/` directory;
saved paper figures were not overwritten. No expensive experiment was executed.

This report predates the replacement GNP generator. References below to an
external original archive describe the validation state at that date; the
publication plan now excludes that payload and provides a clearly labeled
replacement generator instead.

## Environment

`environment.yml` solved and installed successfully with Conda 23.7.3 using the
libmamba solver. The initial solve exposed an incompatibility between PyTorch
2.0.1 and MKL 2026.1.0 (`iJIT_NotifyEvent` was unresolved). The environment file
now constrains `mkl<2024.1`; the resulting environment imports every declared
package successfully.

Resolved direct-package versions:

- Python 3.11.17
- Matplotlib 3.7.3
- NetworkX 3.1
- NumPy 1.24.4
- pandas 1.5.3
- SciPy 1.10.1
- scikit-learn 1.3.2
- PyTorch 2.0.1 (CPU build)
- MKL 2024.0.0

## Figure comparisons

The PNG `pixel match` comparison decodes both images to RGB and compares every
pixel. It is separate from the SHA-256 comparison of the encoded files.

| Figure | Numerical/data result | PNG comparison | PDF comparison |
|---|---|---|---|
| 2 | Reproduces the retained hard-coded recovery arrays; those values remain scientifically unverified | 3361×2498 and pixel-identical; hashes differ | Hash differs |
| 3 | All panels regenerate; Graphlets maxima are 21.5% for (dS=3,dG=15), 0.2% for (dS=5,dG=15), and zero otherwise | Saved 6292×3685; regenerated 4888×2905; not pixel-identical | Hash differs |
| 4 | All 144 matched configurations load and regenerate | 4537×2783 and pixel-identical; hashes differ | Hash differs |
| 5 | All timing/theory inputs load; regenerated aggregate CSV is byte-identical | 5175×3544 and pixel-identical; hashes differ | Hash differs |
| 6 | Twelve runs, a complete 12×12 matrix, and twelve 300-pattern distributions load | 2962×2073 and pixel-identical; hashes differ | Hash differs |

Encoded PNG SHA-256 values:

| Figure | Saved | Clean regeneration |
|---|---|---|
| 2 | `5b07bc94e25b9787af60f3c5759e0d5661c14dfcfbc0b6da99032717c52cae62` | `0448224d103c4f5c2b378ad9700dde5e70428192a907e464d8863ec136b65a38` |
| 3 | `186fdadc3df8922d78a49f234c66535348f7def6c8e06aa8d49c33069d30eec3` | `326598bf42e0f02803af4ffdde7a7b1ed93bc751f20612d773abc237eccfb813` |
| 4 | `7fb31d09cc3143ce0f03a3080e92aed7e4895df667456be26ed89ddf898918c2` | `cb8f4f5696dc17c5824bc26a2cb6b3c9aedbd08cca92d92bf706c5b0177bb9f3` |
| 5 | `dae1bbdb7b1862cbfad22ed19cb10f80c22aa2ff7f1362739a3777515707a3db` | `ec2d5ff9acfb55890bb09c3da14a8d7460da801d28da0185c3f555fa36d8ffe1` |
| 6 | `f839b28fb84b7f6911fa9d24cf1a12c65a8ce7227718ae7497bb0e8065731c88` | `2355a19190b811386e0d539920eba0f335b1832f0629ba48f26a0bc5fe2b9a51` |

Figures 2, 4, 5, and 6 differ at the encoded-file level because the saved files
record Matplotlib 3.7.1 and the clean files record 3.7.3. Their decoded PNG pixel
arrays are exactly equal. PDF hashes also differ; PDF visual equivalence was not
raster-tested because no PDF rasterizer is installed in the declared environment.

The final repository organization retains the manuscript PNGs only; the PDF
copies used during this earlier validation were removed as redundant artifacts.

Figure 3 preserves the maximum survival percentage across the nine
color-distribution pairs for each degree pair. Its remaining visual differences
are a smaller canvas, tighter panel proportions and overlapping top-panel axis
label, absence of the saved A/R/U key, different Graphlets colormap, and smaller
typography. The real-world curves and numerical heatmap contents agree.

## Data and safety checks

- GNP manifest: 12 backgrounds, 12,000 queries, 12 unique query configurations
  with IDs 1–1000, unique paths, valid SHA-256 fields, and 5,580,060,260 declared
  bytes. The graph payload is absent from the Git tree as intended. Checksums
  cannot be re-read against payload files until the external archive is staged.
- Parsed successfully: 183 result JSON files and 583 result CSV files.
- Compact inputs: 144 VISTA synthetic summaries, 144 VISTA case summaries, 144
  VISTA timing summaries, 144 Graphlets filtering summaries, three 100-query
  real-world recovery tables, and twelve VISTA+ runs with 144 G summaries.
- VISTA+ parameters are consistent: alive fraction 0.03, 300 patterns, two miner
  threads, batch size three, preprocessing timeout 10,800 seconds, search timeout
  120 seconds, 160 GiB miner cap, 24 GiB search cap, and 1,000 S graphs per run.
- No credential-like files or content, external symlinks, vendored C++ source, or
  compiled Subgraph Filter Suite binaries were found.
- Python AST and shell syntax checks pass. Executable code/configuration contains
  no absolute user-machine paths. The external C++ build defaults to the
  repository-local ignored `.external/` directory or can be selected explicitly
  with `SGF_BUILD_DIR`.
- 302 compact result files retain original absolute paths as provenance strings.
  Plotting uses local migrated locations and does not dereference those strings.

## Remaining publication issues

1. Recover an authoritative result table for Figure 2 or continue labeling its
   hard-coded recovery values unverified.
2. Decide whether to recreate Figure 3's saved layout exactly or publish the
   numerically equivalent reconstructed layout.
3. Resolve the Table 3 degree-3 edge-count discrepancy (2,240 versus 2,242).
4. Document or recover Figure 5 theory-score generation provenance and timing
   hardware/build details.
5. Complete real-world dataset provenance, licensing, checksums, seeds, and
   extraction accounting.
6. Retain the disclosure that replacement GNP graphs are not the unpublished
   original inputs associated with the saved experimental results.
