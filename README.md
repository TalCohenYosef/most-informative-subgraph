# The Most Informative Subgraph of a Vertex-Colored Graph

Reproducibility materials for the paper **“The Most Informative Subgraph of a
Vertex-Colored Graph: Definition, Bounds, and Estimation.”**

This repository is organized around benchmark-generation code, compact saved
results, and the generated datasets that can be published directly. Expensive
experiments do not need to be rerun to regenerate the paper figures. The
saved-result figure workflow has been validated in a clean Conda environment.
Experiment-level limitations are identified explicitly in
[docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## External implementation

The experiments use the public
[Subgraph Filter Suite](https://github.com/subgraph-filter-suit-project/subgraph_filter_suit)
at the exact commit:

```text
b4a90b08a2d418b137f06edd09044da400b567d8
```

Install it separately; its C++ source is intentionally not vendored here:

```bash
git clone https://github.com/subgraph-filter-suit-project/subgraph_filter_suit.git
cd subgraph_filter_suit
git checkout b4a90b08a2d418b137f06edd09044da400b567d8
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

The expected executables are `sgf-pattern-finder`, `sgf-graph-enumerator`, and
`sgf-graph-searcher`. See the upstream README for complete build requirements.

## Python environment

```bash
conda env create -f environment.yml
conda activate most-informative-subgraph
```

## Data

- `data/generated/toy_models/` contains the compact toy datasets used by Figure 2.
- The original 5.3 GB synthetic GNP payload is not distributed. A replacement
  generator for all twelve configurations is provided under
  `data/generation_code/gnp/`. It reproduces the documented model and layout,
  but not the graph instances underlying the saved paper results.
- `data/generated/gnp/BENCHMARK_MANIFEST.csv` records the filenames, graph
  sizes, and SHA-256 checksums of the unpublished original benchmark. Generated
  replacements are not expected to match those checksums.
- `data/generated/realworld/` contains the final extracted reference and query
  graphs used by the paper. The large source datasets under
  `data/raw/realworld/` are excluded from Git; the extraction code is included.
- `data/results/` contains the compact saved inputs used to build Figures 3–6.

See [the GNP generator documentation](data/generation_code/gnp/README.md) and
[docs/DATA.md](docs/DATA.md).

## Regenerating figures from saved results

Run commands from the repository root:

```bash
python figures/figure_02/plot.py
python figures/figure_03/plot.py
python figures/figure_04/plot.py
python figures/figure_05/plot.py
python figures/figure_06/plot.py
```

Each command writes its PNG beside the corresponding script as
`figures/figure_XX/figure_XX.png`. Use `--output /path/to/file.png` to validate
a script without overwriting the saved manuscript image. Figure 1 is a manually
created conceptual schematic and has no computational generation script.

Figure 2 currently retains the original hard-coded recovery values. They are
unverified pending recovery of the authoritative result table. Figure 3
preserves the paper calculation: each degree cell is the maximum Graphlets
survival percentage across the nine color-distribution pairs.

## Experiment commands

The original experiment runners are preserved under `src/experiments/`. They
still require validation against a clean installation and are not run as part
of figure regeneration. VISTA+ parameters and the original campaign command
are documented in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Manifests

- [docs/FIGURE_MANIFEST.md](docs/FIGURE_MANIFEST.md): figure-to-code/data map
- [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md): original-to-migrated file map
- [docs/CLEAN_ENVIRONMENT_VALIDATION.md](docs/CLEAN_ENVIRONMENT_VALIDATION.md):
  clean-environment results and exact artifact comparisons
- [docs/GITHUB_UPLOAD.md](docs/GITHUB_UPLOAD.md): history-preserving upload procedure
- `docs/FILE_MANIFEST.sha256`: checksums of migrated repository artifacts
- `data/generated/gnp/BENCHMARK_MANIFEST.csv`: manifest of the unpublished
  original GNP benchmark

## Current status

The initial migration is intentionally conservative: original numerical data
and algorithms are preserved, while machine-specific paths in copied figure
scripts have been replaced with repository-relative paths. Remaining issues
and validation boundaries are listed in
[docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).
