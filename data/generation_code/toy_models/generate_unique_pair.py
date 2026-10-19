#!/usr/bin/env python3

import json
import random
from pathlib import Path


SEED = 42
N_QUERIES = 1000

random.seed(SEED)

DATA_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = DATA_ROOT / "generated" / "toy_models"
DATASET_DIR = BASE_DIR / "unique_pair"
S_DIR = DATASET_DIR / "S_graphs"


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


def generate_g_colors(n):
    return random.choices(
        population=[0, 1, 2, 3],
        weights=[0.45, 0.45, 0.05, 0.05],
        k=n
    )


def generate_gnp_edges(n, p, colors=None, excluded_edge=None):
    """Generate an undirected G(n,p) graph with independent edge trials."""
    edges = []

    for u in range(n):
        for v in range(u + 1, n):
            if excluded_edge == (u, v):
                continue
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


def generate_connected_gnp_edges(n, p, colors):
    """Generate G(n,p), adding permitted edges until it is connected."""
    edges = set(generate_gnp_edges(n, p, colors=colors))
    components = [{vertex} for vertex in range(n)]

    for u, v in edges:
        left = next(component for component in components if u in component)
        right = next(component for component in components if v in component)
        if left is not right:
            left.update(right)
            components.remove(right)

    while len(components) > 1:
        left = components[0]
        right_index = next(
            index for index, right in enumerate(components[1:], start=1)
            if any({colors[u], colors[v]} != {2, 3}
                   for u in left for v in right)
        )
        right = components[right_index]
        u = next(u for u in left for v in right
                 if {colors[u], colors[v]} != {2, 3})
        v = next(v for v in right if {colors[u], colors[v]} != {2, 3})
        edges.add((min(u, v), max(u, v)))
        left.update(right)
        components.remove(right)

    return list(edges)


def generate_background():
    """
    G:
        n = 1000
        colors sampled with probabilities
        P(0)=0.45, P(1)=0.45, P(2)=0.05, P(3)=0.05
        all permitted edges sampled independently
        p = 0.003
    """

    n_g = 1000
    p_g = 0.003

    colors = generate_g_colors(n_g)
    edges = generate_connected_gnp_edges(n_g, p_g, colors)

    save_graph(
        DATASET_DIR / "G.json",
        colors,
        edges
    )

    n0 = colors.count(0)
    n1 = colors.count(1)

    print("Background G created")
    print(f"Vertices: {n_g}")
    print(f"Color 0:  {n0}")
    print(f"Color 1:  {n1}")
    print(f"Color 2:  {colors.count(2)}")
    print(f"Color 3:  {colors.count(3)}")
    print(f"Edges:    {len(edges)}")


def generate_queries():
    """
    Each S_i:
        n = 30
        colors = {0,1} uniformly
        all edges sampled independently with p = 0.1

    Then plant exactly one edge between a color-2 vertex and a color-3 vertex.
    """

    n_s = 30
    p_s = 0.1

    ground_truth = {}

    for i in range(1, N_QUERIES + 1):

        colors = [
            random.choice([0, 1])
            for _ in range(n_s)
        ]
        u, v = sorted(random.sample(range(n_s), 2))
        colors[u] = 2
        colors[v] = 3

        # Sample every other edge independently, then plant the unique 2-3 edge.
        edges = generate_gnp_edges(n_s, p_s, excluded_edge=(u, v))
        edges.append((u, v))
        edges = connect_graph(n_s, edges)

        save_graph(
            S_DIR / f"S_{i}.json",
            colors,
            edges
        )

        # Save the planted pair U_i*
        ground_truth[str(i)] = [u, v]

    with open(
        DATASET_DIR / "ground_truth.json",
        "w"
    ) as f:
        json.dump(
            ground_truth,
            f,
            indent=2
        )

    print()
    print(f"Created {N_QUERIES} query graphs.")
    print("Unique-pair dataset finished.")


if __name__ == "__main__":

    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    S_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    generate_background()
    generate_queries()
