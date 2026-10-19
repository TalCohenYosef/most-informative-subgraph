# Synthetic GNP replacement generator

`generate_gnp_benchmark.py` creates a reproducible **replacement** for the
synthetic benchmark described in the manuscript. It supports all twelve
combinations of color family (`average`, `rare`, or `uniform`) and target
average degree (3, 5, 8, or 15). By default it writes one 50,000-vertex
reference graph and 1,000 numbered query graphs with 1,500–2,000 vertices for
every selected configuration.

## Scientific scope

The generated graphs are not the original graph instances used to produce the
saved paper results in `data/results/`. The original seed was not preserved,
and the manuscript does not specify how endpoints of connectivity-repair edges
were selected. The manuscript draft explicitly leaves that detail unresolved.
Therefore this generator must not be used to claim bitwise reproduction of the
original benchmark or to relabel the saved experimental summaries.

The implementation makes these explicit choices:

- independently sample every possible undirected edge with
  `p = target_degree / (n - 1)` using geometric skipping;
- if the sample is disconnected, randomly order its connected components,
  choose one vertex uniformly within each component, and join consecutive
  components with `components - 1` additional edges;
- sample the query size uniformly from the inclusive range 1,500–2,000;
- sample each vertex color independently using the rounded percentages in
  manuscript Table 4, normalized to sum to one;
- use NumPy's `PCG64` generator through `default_rng`. Each graph receives a
  deterministic stream derived from the master seed, family, degree, and query
  number, so generating one configuration produces the same files as selecting
  it during an all-configuration run.

The original reference files have exactly the approximate Table 5 edge counts,
while the documented GNP procedure naturally produces a random edge count.
This generator follows the stated GNP-plus-connectivity-repair procedure and
does not force those counts. The unpublished original procedure may have
contained an additional adjustment that cannot be recovered from the current
materials.

## Output compatibility

The legacy layout and filenames are preserved:

```text
data/generated/gnp/
├── references/graphs_deg_5/G_<family>_deg_<degree>.json
└── queries/input_color_<family>_deg_<degree>/S_<1..1000>.json
```

Each JSON document contains `nodes` (`id`, `color`) and `links` (`source`,
`target`), matching the original node-link schema. The unusual directory name
`graphs_deg_5` is retained solely for compatibility with the existing
benchmark layout.

`BENCHMARK_MANIFEST.csv` describes the unpublished original files and their
checksums. Newly generated files are expected **not** to match those checksums.

## Commands

Run from the repository root. A master seed is mandatory because no
authoritative original seed is known.

Generate all twelve full configurations (large and intentionally not run as
part of repository validation):

```bash
python data/generation_code/gnp/generate_gnp_benchmark.py --seed 2026
```

Generate only Average/degree-3 into an empty external directory:

```bash
python data/generation_code/gnp/generate_gnp_benchmark.py \
  --seed 2026 --families average --degrees 3 \
  --output-root /path/to/empty/gnp
```

For a small smoke test, reduce graph sizes and query count and write outside
the benchmark directory:

```bash
python data/generation_code/gnp/generate_gnp_benchmark.py \
  --seed 2026 --families average --degrees 3 --queries 3 \
  --reference-vertices 100 --query-min-vertices 20 \
  --query-max-vertices 25 --output-root /tmp/gnp-smoke
```

Existing graph files are never replaced unless `--overwrite` is passed
explicitly. The generator writes each graph through a temporary file followed
by an atomic rename.
