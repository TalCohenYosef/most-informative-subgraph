#!/usr/bin/env python3

import json
import random
from pathlib import Path

SEED = 42
N_QUERIES = 1000

random.seed(SEED)

DATA_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = DATA_ROOT / "generated" / "toy_models"


def generate_gnp_edges(n, p, colors=None):
    edges = []

    for u in range(n):
        for v in range(u + 1, n):
            if colors is not None and {colors[u], colors[v]} == {2, 3}:
                continue
            if random.random() < p:
                edges.append((u, v))

    return edges


def connect_graph(n, edges):
    """Add the minimum number of edges needed to connect the graph."""
    adjacency = [[] for _ in range(n)]
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)

    representatives = []
    visited = set()
    for start in range(n):
        if start in visited:
            continue
        representatives.append(start)
        visited.add(start)
        stack = [start]
        while stack:
            u = stack.pop()
            for v in adjacency[u]:
                if v not in visited:
                    visited.add(v)
                    stack.append(v)

    for u, v in zip(representatives, representatives[1:]):
        edges.append((u, v))

    return edges


def save_graph(path, colors, edges):
    graph = {
        "nodes": [
            {
                "id": i,
                "color": colors[i]
            }
            for i in range(len(colors))
        ],
        "links": [
            {
                "source": u,
                "target": v
            }
            for u, v in edges
        ]
    }

    with open(path, "w") as f:
        json.dump(graph, f)


def generate_unique_color():
    dataset_dir = BASE_DIR / "unique_color"
    s_dir = dataset_dir / "S_graphs"

    s_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================
    # Background graph G ~ G(1000, 0.003)
    # ========================================================

    n_g = 1000
    p_g = 0.003

    # Color 2 is reserved for the planted vertex and must be absent from G.
    colors_g = random.choices(
        population=[0, 1, 3],
        weights=[0.475, 0.475, 0.05],
        k=n_g
    )

    # Do not allow an edge between a color-2 vertex and a color-3 vertex.
    edges_g = connect_graph(n_g, generate_gnp_edges(n_g, p_g, colors_g))

    save_graph(
        dataset_dir / "G.json",
        colors_g,
        edges_g
    )

    print(
        f"G created: "
        f"{n_g} vertices, {len(edges_g)} edges"
    )

    # ========================================================
    # Query graphs S_i ~ G(30, 0.1)
    # ========================================================

    ground_truth = {}

    for i in range(1, N_QUERIES + 1):

        n_s = 30
        p_s = 0.1

        colors_s = [
            random.choice([0, 1])
            for _ in range(n_s)
        ]

        edges_s = connect_graph(n_s, generate_gnp_edges(n_s, p_s))

        # Plant the unique color
        planted_vertex = random.randrange(n_s)
        colors_s[planted_vertex] = 2

        save_graph(
            s_dir / f"S_{i}.json",
            colors_s,
            edges_s
        )

        ground_truth[str(i)] = [planted_vertex]

    with open(
        dataset_dir / "ground_truth.json",
        "w"
    ) as f:
        json.dump(
            ground_truth,
            f,
            indent=2
        )

    print(f"Created {N_QUERIES} query graphs.")
    print("Unique-color dataset finished.")


if __name__ == "__main__":
    generate_unique_color()
