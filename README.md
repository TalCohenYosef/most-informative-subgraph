# The Most Informative Subgraph of a Vertex-Colored Graph

Reproducibility materials for the paper **“The Most Informative Subgraph of a
Vertex-Colored Graph: Definition, Bounds, and Estimation.”**

This repository provides dataset-generation and extraction code, compact saved
experimental results, analysis utilities, and scripts for regenerating Figures
2–6. The saved-result workflow is described in
[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Installation

Create the Python environment from the repository root:

```bash
conda env create -f environment.yml
conda activate most-informative-subgraph
```


The original experiments used the public [Subgraph Filter Suite](https://github.com/subgraph-filter-suit-project/subgraph_filter_suit) at commit `b4a90b08a2d418b137f06edd09044da400b567d8`. 
This repository contains the C++ implementations of VISTA, VISTA+, and Graphlets Enumeration. It is not required for dataset generation or figure reproduction. 
Its C++ source is not included here; install it separately to inspect the original implementation:


```bash
git clone https://github.com/subgraph-filter-suit-project/subgraph_filter_suit.git
cd subgraph_filter_suit
git checkout b4a90b08a2d418b137f06edd09044da400b567d8
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

The expected executables are `sgf-pattern-finder`, `sgf-graph-enumerator`, and
`sgf-graph-searcher`. See the upstream repository for complete build
requirements.

## Data and benchmark preparation

### Synthetic GNP benchmark

The benchmark crosses two independent sets of configurations:

- 12 reference-graph configurations: 3 vertex-color distributions (Average,
  Rare, and Uniform) × 4 average degrees (3, 5, 8, and 15).
- 12 query-graph configurations with the same 3 × 4 design. Each query
  configuration contains 1,000 graphs.

Every query configuration is evaluated against every reference configuration.
This gives **12 × 12 = 144 experimental configuration pairs**, or **144,000
individual query-reference evaluations** when all 1,000 queries are evaluated
for every pair.

The original approximately 5.3 GB GNP graph instances used for the reported
experiments are not distributed. The replacement generator samples graphs
randomly from the documented graph parameters and color distributions. Because
GNP generation is stochastic, newly generated instances may differ from the
original experimental graphs even though they follow the same documented
model. The saved paper results in `data/results/` continue to describe the
original experiments, not newly generated replacements.

Generate all 12 reference configurations and all 12 sets of 1,000 queries with
a chosen seed:

```bash
python data/generation_code/gnp/generate_gnp_benchmark.py --seed 2026
```

The generator also supports individual configurations and smaller tests. See
[the GNP generator documentation](data/generation_code/gnp/README.md).

### Real-world datasets

The real-world pipeline is organized as follows:

```text
data/raw/realworld/                 original source graph data
data/generation_code/realworld/    extraction code
data/generated/realworld/          extracted reference and query graphs
```

The final extracted BookChild, SportsFit, and ogbn-arxiv graphs used in the
paper are included under `data/generated/realworld/`. The extraction program
expects each source graph as
`data/raw/realworld/<dataset>/processed_data.pt` and writes one `G.json`, 100
query graphs, and extraction summaries to
`data/generated/realworld/<dataset>/`.

The required raw source graph files exceed ordinary GitHub file-size limits and
are not tracked in this repository. Download BookChild and SportsFit from the
authoritative Graph-COM dataset:

```bash
mkdir -p data/raw/realworld/bookchild data/raw/realworld/sportsfit

curl -L --fail \
  https://huggingface.co/datasets/Graph-COM/Text-Attributed-Graphs/resolve/main/bookchild/processed_data.pt?download=true \
  -o data/raw/realworld/bookchild/processed_data.pt

curl -L --fail \
  https://huggingface.co/datasets/Graph-COM/Text-Attributed-Graphs/resolve/main/sportsfit/processed_data.pt?download=true \
  -o data/raw/realworld/sportsfit/processed_data.pt
```

For ogbn-arxiv, use the official OGB loader. Its authoritative archive is
<https://snap.stanford.edu/ogb/data/nodeproppred/arxiv.zip>. The following
stores the loaded PyG graph where the extractor expects it:

```bash
python -m pip install ogb
mkdir -p data/raw/realworld/ogbn_arxiv
python - <<'PY'
from pathlib import Path

import torch
from ogb.nodeproppred import PygNodePropPredDataset

destination = Path("data/raw/realworld/ogbn_arxiv")
dataset = PygNodePropPredDataset(name="ogbn-arxiv", root=str(destination / "ogb"))
graph = dataset[0]
graph.y = graph.y.view(-1)
torch.save(graph, destination / "processed_data.pt")
PY
```

Only graph structure and node labels from these files are used by the
extraction pipeline; text and embedding files are not required. After the
inputs are installed, list the extraction options with:

```bash
python data/generation_code/realworld/extract_disjoint_color_graphs_random_frontier.py --help
```

The extractor supports `--dataset bookchild`, `--dataset sportsfit`, and
`--dataset ogbn_arxiv`. Dataset sources, manuscript citations, licenses, and
the data inventory are documented in [docs/DATA.md](docs/DATA.md); experiment
notes are in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

### Other included data

- `data/generated/toy_models/` contains the three toy datasets used by Figure 2.
- `data/results/` contains the compact saved results used to build Figures 3–6.

## Regenerating figures from saved results

Run the following commands from the repository root:

```bash
python figures/figure_02/plot.py
python figures/figure_03/plot.py
python figures/figure_04/plot.py
python figures/figure_05/plot.py
python figures/figure_06/plot.py
```

Each command writes `figures/figure_XX/figure_XX.png`. Use
`--output /path/to/file.png` to write elsewhere without replacing the saved
image. Figure 1 is a manually created conceptual schematic and has no
generation script.

## Saved-result analysis

Reusable analysis utilities are stored in `figures/analysis/`; compact inputs
are in `data/results/`. Their roles and the saved-result workflow are described
in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) and
[docs/FIGURE_MANIFEST.md](docs/FIGURE_MANIFEST.md).

## Reproducibility scope

Figures 2–6 can be regenerated from the included datasets and saved results.
This figure-level workflow does not establish that every underlying experiment
or reported value has been independently rerun. The replacement GNP generator
creates new stochastic benchmark instances and does not recreate the
undistributed original instances. Detailed boundaries and unresolved items are
listed in [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

