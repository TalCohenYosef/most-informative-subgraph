# Reproducibility status and unresolved issues

## Agreed scope

- Figure 1 is a manual schematic and is resolved.
- The original synthetic GNP payload is not distributed. The provided generator
  creates a documented replacement, not the exact inputs behind saved results.
- Subgraph Filter Suite is an external pinned dependency and is not vendored.
- Figure 6 is reproduced from saved summaries; pattern JSON files are outside
  scope and are not a blocker.

## Migration provenance

Repository artifacts were copied from the original experiment workspace; the
original files were not modified. Scientific calculations were retained, while
machine-specific path and import defaults were adjusted only in repository
copies where required for portability.

## Remaining issues

### Figure 2

The recovery result CSVs in the original experiment tree are empty. The plotting
script falls back to hard-coded values. These values are retained unchanged but
remain explicitly unverified until an authoritative result table is recovered.

The Unique-Color generator also appears to include color 3 in its background
sampling weights, while the manuscript describes initial colors 0 and 1. The
fixed toy files used by the figure are preserved; this generator/manuscript
difference requires scientific review before claiming dataset regeneration.

### Figure 3

The original exact composite script was absent and has been reconstructed from
the saved component data. The agreed Graphlets reduction is the maximum survival
percentage across color-distribution pairs. Clean-environment validation confirms
the numerical panels, but the reconstructed composite is not visually identical
to the saved reference. Its remaining differences are layout, typography, the
A/R/U key, and the Graphlets colormap. The manuscript caption/discussion will be
corrected separately and is not changed here.

### Table 3

The fixed numbered degree-3 query files have 2,242–3,205 edges, whereas the
current manuscript reports 2,240–3,205. An author decision is required.

### Synthetic GNP generation

The manuscript specifies graph sizes, target degrees, color probabilities, and
that disconnected GNP samples were repaired with additional edges. It does not
specify the original random seed or the endpoint-selection rule for those added
edges. The replacement generator uses a mandatory user-supplied seed and joins
randomly ordered components through uniformly selected component vertices. The
original reference files also contain exactly the approximate Table 5 edge
counts, suggesting an undocumented adjustment beyond the stated GNP procedure.
These differences are disclosed in the generator README and prevent claims of
exact dataset or experiment reproduction from newly generated graphs.

### Figure 5

The saved inputs reproduce the plot, but the theory-score generation dependency
`analyze_gnp_vista_lambda.py` was not present in the original tree. Timing
hardware, compiler/build mode, thread counts, and timing boundaries must be
documented before interpreting runtime measurements as independently repeatable.

### Real-world benchmark

The repository contains final extracted reference/query graph payloads, their
summaries, original-label recovery results, and extraction code. Original raw
source datasets are excluded from Git because of their size. Sources, licenses,
and acquisition instructions are documented in `DATA.md` and the main README.
The exact extraction seed and candidate-rejection counts remain undocumented.

### Validation boundary

No expensive experiment has been rerun. A clean Conda environment created from
`environment.yml` regenerated Figures 2–6 from the migrated saved results.
Figures 2, 4, 5, and 6 have pixel-identical PNG renderings; encoded PNG and PDF
hashes differ because the saved artifacts were produced by Matplotlib 3.7.1 and
the clean environment resolves 3.7.3. Figure 5's derived aggregate CSV is
byte-identical. Figure 3 is numerically reproducible but retains the layout
differences described above. No status is upgraded to “fully reproducible”
because the underlying experiments were not rerun.

The validated environment resolved Python 3.11.17, Matplotlib 3.7.3, NetworkX
3.1, NumPy 1.24.4, pandas 1.5.3, SciPy 1.10.1, scikit-learn 1.3.2, PyTorch
2.0.1 (CPU), and MKL 2024.0.0. The `mkl<2024.1` constraint in
`environment.yml` avoids an incompatibility observed with PyTorch 2.0.1 and
newer MKL releases.
