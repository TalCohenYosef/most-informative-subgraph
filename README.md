# The Most Informative Subgraph of a Vertex-Colored Graph: Definition, Bounds, and Estimation

This repository contains the source code, experimental data, and figure-generation scripts associated with the paper **"The Most Informative Subgraph of a Vertex-Colored Graph: Definition, Bounds, and Estimation."**

The repository is organized to support the reproducibility of the experimental results and figures presented in the paper.

## Repository Structure

```text
most-informative-subgraph/
├── README.md
├── .gitignore
├── data/
├── src/
└── figures/
```

- **`data/`** — Input datasets and experimental results.
- **`src/`** — Source code for generating data and running experiments.
- **`figures/`** — Scripts for reproducing the figures presented in the paper.

## Installation

Clone the repository:

```bash
git clone https://github.com/TalCohenYosef/most-informative-subgraph.git
cd most-informative-subgraph
```

### External Dependency: Subgraph Filter Suite

The experiments use the publicly available [Subgraph Filter Suite](https://github.com/subgraph-filter-suit-project/subgraph_filter_suit), a C++ library for subgraph matching and filtering.

The exact version used in the experiments is:

- **Commit:** `b4a90b08a2d418b137f06edd09044da400b567d8`

To obtain the dependency:

```bash
git clone https://github.com/subgraph-filter-suit-project/subgraph_filter_suit.git
cd subgraph_filter_suit
git checkout b4a90b08a2d418b137f06edd09044da400b567d8
```

Build requirements and compilation instructions are provided below.

#### Build Requirements

The Subgraph Filter Suite library requires:

- CMake 3.16 or newer
- A C++17-compatible compiler (GCC 7+, Clang 5+, or MSVC 19.14+)
- Boost 1.76 or newer, including Graph, Log, Log Setup, JSON, and Program Options (for CLI tools)
- Internet access during the initial build to retrieve GoogleTest

CUDA is optional and is required only for GPU-accelerated processing.

#### Building the C++ Tools

From the `subgraph_filter_suit` directory, run:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel
```

The build produces three executables:

- `sgf-graph-enumerator` — Motif and path enumeration and filtering.
- `sgf-pattern-finder` — Pattern preprocessing and filtering.
- `sgf-graph-searcher` — Exact subgraph isomorphism.


## Reproducing the Experimental Results

The `src/` directory will contain the scripts used to generate the experimental results.

Detailed execution instructions, configurations, and parameters will be added as the experimental code is organized.

## Reproducing the Figures

The `figures/` directory will contain the scripts used to reproduce the figures presented in the paper.

## Data

The `data/` directory will contain the input datasets and experimental results required for reproduction.
