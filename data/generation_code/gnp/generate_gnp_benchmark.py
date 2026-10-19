#!/usr/bin/env python3
"""Generate a reproducible replacement for the synthetic GNP benchmark.

The original random seed and the precise connectivity-repair procedure were
not preserved.  Consequently, this program reproduces the documented model,
parameters, file layout, and JSON schema, but not the original graph instances.
See README.md in this directory before using generated data.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


FAMILIES = ("average", "rare", "uniform")
DEGREES = (3, 5, 8, 15)

# Table 4 of the manuscript. The published percentages are rounded, so they
# are normalized before sampling.
COLOR_PERCENTAGES = {
    "uniform": [5.00] * 20,
    "average": [
        19.52, 17.57, 14.65, 11.73, 9.73, 5.85, 4.87, 3.89, 2.93, 1.95,
        0.98, 0.98, 0.97, 0.97, 0.97, 0.49, 0.48, 0.49, 0.49, 0.49,
    ],
    "rare": [
        24.97, 16.68, 14.57, 12.53, 10.42, 5.21, 5.21, 4.15, 3.12, 2.09,
        0.10, 0.10, 0.10, 0.10, 0.11, 0.11, 0.10, 0.10, 0.10, 0.11,
    ],
}


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.weight = [1] * size

    def find(self, item: int) -> int:
        parent = self.parent
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left = self.find(left)
        right = self.find(right)
        if left == right:
            return
        if self.weight[left] < self.weight[right]:
            left, right = right, left
        self.parent[right] = left
        self.weight[left] += self.weight[right]


def fast_gnp_edges(
    vertex_count: int, probability: float, rng: np.random.Generator
) -> tuple[list[tuple[int, int]], UnionFind]:
    """Sample simple undirected G(n,p) edges with geometric skipping."""
    if not 0.0 <= probability <= 1.0:
        raise ValueError("edge probability must be between zero and one")

    components = UnionFind(vertex_count)
    edges: list[tuple[int, int]] = []
    if probability == 0.0:
        return edges, components
    if probability == 1.0:
        for target in range(1, vertex_count):
            for source in range(target):
                edges.append((source, target))
                components.union(source, target)
        return edges, components

    log_q = math.log1p(-probability)
    target = 1
    source = -1
    while target < vertex_count:
        source += 1 + int(math.log1p(-rng.random()) / log_q)
        while source >= target and target < vertex_count:
            source -= target
            target += 1
        if target < vertex_count:
            edges.append((source, target))
            components.union(source, target)
    return edges, components


def connect_components(
    vertex_count: int,
    edges: list[tuple[int, int]],
    components: UnionFind,
    rng: np.random.Generator,
) -> int:
    """Connect components in random order using random vertices in each one."""
    members: dict[int, list[int]] = {}
    for vertex in range(vertex_count):
        members.setdefault(components.find(vertex), []).append(vertex)
    groups = list(members.values())
    if len(groups) <= 1:
        return 0

    rng.shuffle(groups)
    representatives = [group[int(rng.integers(len(group)))] for group in groups]
    for left, right in zip(representatives, representatives[1:]):
        edges.append((min(left, right), max(left, right)))
    return len(groups) - 1


def write_graph(
    path: Path,
    colors: np.ndarray,
    edges: Sequence[tuple[int, int]],
    overwrite: bool,
) -> None:
    """Write the legacy node-link JSON schema atomically."""
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite existing graph: {path}\n"
            "Choose an empty --output-root or pass --overwrite explicitly."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write('{\n  "nodes": [\n')
            for index, color in enumerate(colors):
                comma = "," if index + 1 < len(colors) else ""
                handle.write(
                    f'    {{\n      "id": {index},\n      "color": {int(color)}\n'
                    f"    }}{comma}\n"
                )
            handle.write('  ],\n  "links": [\n')
            for index, (source, target) in enumerate(edges):
                comma = "," if index + 1 < len(edges) else ""
                handle.write(
                    f'    {{\n      "source": {source},\n      "target": {target}\n'
                    f"    }}{comma}\n"
                )
            handle.write("  ]\n}\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def generate_graph(
    path: Path,
    vertex_count: int,
    target_degree: int,
    probabilities: np.ndarray,
    rng: np.random.Generator,
    overwrite: bool,
) -> tuple[int, int]:
    colors = rng.choice(20, size=vertex_count, p=probabilities)
    edge_probability = target_degree / (vertex_count - 1)
    edges, components = fast_gnp_edges(vertex_count, edge_probability, rng)
    repair_edges = connect_components(vertex_count, edges, components, rng)
    write_graph(path, colors, edges, overwrite)
    return len(edges), repair_edges


def graph_rng(seed: int, family: str, degree: int, query_id: int) -> np.random.Generator:
    """Give every graph a stable stream, independent of selection/order."""
    family_id = FAMILIES.index(family)
    degree_id = DEGREES.index(degree)
    return np.random.default_rng(
        np.random.SeedSequence([seed, family_id, degree_id, query_id])
    )


def normalized_probabilities(family: str) -> np.ndarray:
    probabilities = np.asarray(COLOR_PERCENTAGES[family], dtype=float)
    return probabilities / probabilities.sum()


def parse_args() -> argparse.Namespace:
    data_dir = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, help="master random seed")
    parser.add_argument(
        "--families", nargs="+", choices=FAMILIES, default=list(FAMILIES)
    )
    parser.add_argument(
        "--degrees", nargs="+", type=int, choices=DEGREES, default=list(DEGREES)
    )
    parser.add_argument("--queries", type=int, default=1000)
    parser.add_argument("--reference-vertices", type=int, default=50_000)
    parser.add_argument("--query-min-vertices", type=int, default=1_500)
    parser.add_argument("--query-max-vertices", type=int, default=2_000)
    parser.add_argument(
        "--output-root", type=Path, default=data_dir / "generated" / "gnp"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly allow replacement of graph files selected by this command",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.seed < 0:
        raise ValueError("--seed must be non-negative")
    if args.queries < 0:
        raise ValueError("--queries must be non-negative")
    if args.reference_vertices < 2:
        raise ValueError("--reference-vertices must be at least 2")
    if not 2 <= args.query_min_vertices <= args.query_max_vertices:
        raise ValueError("query vertex bounds must satisfy 2 <= min <= max")
    if max(args.degrees) >= min(args.reference_vertices, args.query_min_vertices):
        raise ValueError("target degree must be smaller than every graph")


def selected_targets(args: argparse.Namespace) -> Iterable[tuple[str, int]]:
    for family in FAMILIES:
        if family not in args.families:
            continue
        for degree in DEGREES:
            if degree in args.degrees:
                yield family, degree


def graph_paths(
    output_root: Path, family: str, degree: int, query_count: int
) -> Iterable[Path]:
    yield (
        output_root
        / "references"
        / "graphs_deg_5"
        / f"G_{family}_deg_{degree}.json"
    )
    query_dir = output_root / "queries" / f"input_color_{family}_deg_{degree}"
    for query_id in range(1, query_count + 1):
        yield query_dir / f"S_{query_id}.json"


def main() -> None:
    args = parse_args()
    validate_args(args)
    output_root = args.output_root.resolve()
    targets = list(selected_targets(args))

    if not args.overwrite:
        existing = [
            path
            for family, degree in targets
            for path in graph_paths(output_root, family, degree, args.queries)
            if path.exists()
        ]
        if existing:
            preview = "\n".join(f"  {path}" for path in existing[:10])
            suffix = "\n  ..." if len(existing) > 10 else ""
            raise FileExistsError(
                f"refusing to overwrite {len(existing)} existing target file(s):\n"
                f"{preview}{suffix}\nChoose an empty --output-root or pass "
                "--overwrite explicitly."
            )

    for family, degree in targets:
        probabilities = normalized_probabilities(family)
        reference_path = (
            output_root
            / "references"
            / "graphs_deg_5"
            / f"G_{family}_deg_{degree}.json"
        )
        edge_count, repairs = generate_graph(
            reference_path,
            args.reference_vertices,
            degree,
            probabilities,
            graph_rng(args.seed, family, degree, 0),
            args.overwrite,
        )
        print(
            f"wrote {reference_path}: n={args.reference_vertices}, "
            f"m={edge_count}, connectivity_edges={repairs}"
        )

        query_dir = output_root / "queries" / f"input_color_{family}_deg_{degree}"
        for query_id in range(1, args.queries + 1):
            rng = graph_rng(args.seed, family, degree, query_id)
            vertex_count = int(
                rng.integers(args.query_min_vertices, args.query_max_vertices + 1)
            )
            query_path = query_dir / f"S_{query_id}.json"
            edge_count, repairs = generate_graph(
                query_path,
                vertex_count,
                degree,
                probabilities,
                rng,
                args.overwrite,
            )
            print(
                f"wrote {query_path}: n={vertex_count}, m={edge_count}, "
                f"connectivity_edges={repairs}"
            )


if __name__ == "__main__":
    main()
