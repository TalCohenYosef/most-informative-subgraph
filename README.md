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

The experimental pipeline uses subgraph_filter_suit, a C++ library for subgraph matching and filtering.

The experiments reported in the paper were conducted using the following version:

Repository: yaelgin2/subgraph_filter_suit

Branch: develop

Commit: b4a90b08a2d418b137f06edd09044da400b567d8

The specified commit identifies the exact version used in the experiments, ensuring that the dependency can be reproduced independently of future updates to the library.

Requirements

CMake 3.16 or newer

C++17-compatible compiler (GCC 7+, Clang 5+, or MSVC 19.14+)

Boost 1.76 or newer, including Graph, Log, Log Setup, and JSON

Boost Program Options for the command-line tools

Internet access during the initial build to retrieve GoogleTest

CUDA is optional and is required only for GPU-accelerated processing.

Installation and Build

Clone the dependency repository (requires access to the private repository):

git clone git@github.com:yaelgin2/subgraph_filter_suit.git
cd subgraph_filter_suit

Check out the exact version used in the experiments:

git checkout b4a90b08a2d418b137f06edd09044da400b567d8

Build the C++ tools:

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel

The build produces three command-line tools:

sgf-graph-enumerator — Motif and path enumeration and filtering.

sgf-pattern-finder — Pattern preprocessing and filtering.

sgf-graph-searcher — Exact subgraph isomorphism.

For additional configuration and usage instructions, refer to the dependency's documentation.

Access note: The dependency repository is currently private. Access to the exact source version must be provided to reviewers through an approved distribution method.
## Reproducing the Experimental Results

The `src/` directory will contain the scripts used to generate the experimental results.

Detailed execution instructions, configurations, and parameters will be added as the experimental code is organized.

## Reproducing the Figures

The `figures/`
