#!/usr/bin/env python3

import json
import random
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

SEED = 42
N_QUERIES = 1000

# Background G
G_NUM_COLOR_0 = 100
G_NUM_COLOR_1 = 900

# Query S_i
S_NUM_COLOR_0 = 3
S_NUM_COLOR_1 = 27

# Target average degree of the bipartite base graphs
TARGET_AVG_DEGREE = 3

# Number of rare 0-0 edges planted in G.
# These edges form a matching, so G contains 0-0 edges
# but cannot contain a 0-0-0 triangle.
G_NUM_RARE_00_EDGES = 10

random.seed(SEED)

DATA_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = DATA_ROOT / "generated" / "toy_models"

DATASET_DIR = BASE_DIR / "unique_triangle"
S_DIR = DATASET_DIR / "S_graphs"


# ============================================================
# Save graph
# ============================================================

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
            for u, v in sorted(edges)
        ]
    }

    with open(path, "w") as f:
        json.dump(graph, f)


# ============================================================
# Connected bipartite graph
# ============================================================

def generate_connected_bipartite_graph(
    num_color_0,
    num_color_1,
    target_average_degree
):
    """
    Create a connected graph whose initial edges are ONLY 0-1.

    Color 0 and color 1 are also the two bipartite partitions.

    Step 1:
        Build a spanning tree -> guarantees connectivity.

    Step 2:
        Add random 0-1 edges until approximately the
        requested average degree is reached.
    """

    n = num_color_0 + num_color_1

    color_0_vertices = list(range(num_color_0))

    color_1_vertices = list(
        range(
            num_color_0,
            num_color_0 + num_color_1
        )
    )

    colors = (
        [0] * num_color_0
        + [1] * num_color_1
    )

    edges = set()

    # --------------------------------------------------------
    # Step 1: connected spanning structure
    # --------------------------------------------------------

    # Start with one vertex from each side.
    first_0 = random.choice(color_0_vertices)
    first_1 = random.choice(color_1_vertices)

    edges.add(
        (
            min(first_0, first_1),
            max(first_0, first_1)
        )
    )

    connected_0 = [first_0]
    connected_1 = [first_1]

    remaining_0 = [
        v for v in color_0_vertices
        if v != first_0
    ]

    remaining_1 = [
        v for v in color_1_vertices
        if v != first_1
    ]

    random.shuffle(remaining_0)
    random.shuffle(remaining_1)

    # Connect every remaining color-0 vertex
    # to an already connected color-1 vertex.
    for u in remaining_0:

        v = random.choice(connected_1)

        edges.add(
            (
                min(u, v),
                max(u, v)
            )
        )

        connected_0.append(u)

    # Connect every remaining color-1 vertex
    # to an already connected color-0 vertex.
    for v in remaining_1:

        u = random.choice(connected_0)

        edges.add(
            (
                min(u, v),
                max(u, v)
            )
        )

        connected_1.append(v)

    # At this point the graph is guaranteed to be connected.

    # --------------------------------------------------------
    # Step 2: add random 0-1 edges
    # --------------------------------------------------------

    target_edges = round(
        n * target_average_degree / 2
    )

    minimum_connected_edges = n - 1

    target_edges = max(
        target_edges,
        minimum_connected_edges
    )

    max_bipartite_edges = (
        num_color_0 * num_color_1
    )

    target_edges = min(
        target_edges,
        max_bipartite_edges
    )

    possible_edges = []

    for u in color_0_vertices:
        for v in color_1_vertices:

            edge = (
                min(u, v),
                max(u, v)
            )

            if edge not in edges:
                possible_edges.append(edge)

    random.shuffle(possible_edges)

    needed = target_edges - len(edges)

    for edge in possible_edges[:needed]:
        edges.add(edge)

    return (
        colors,
        edges,
        color_0_vertices,
        color_1_vertices
    )


# ============================================================
# Background G
# ============================================================

def generate_background():

    (
        colors,
        edges,
        color_0_vertices,
        _
    ) = generate_connected_bipartite_graph(
        G_NUM_COLOR_0,
        G_NUM_COLOR_1,
        TARGET_AVG_DEGREE
    )

    # --------------------------------------------------------
    # Add rare 0-0 edges to G
    # --------------------------------------------------------
    #
    # Important:
    # We use a MATCHING.
    #
    # For example:
    #
    #     0---0     0---0     0---0
    #
    # No color-0 vertex participates in two such edges.
    #
    # Therefore a 0-0 edge exists in G,
    # but a 0-0-0 triangle cannot exist.
    # --------------------------------------------------------

    rare_vertices = color_0_vertices.copy()

    random.shuffle(rare_vertices)

    required_vertices = 2 * G_NUM_RARE_00_EDGES

    if required_vertices > len(rare_vertices):
        raise ValueError(
            "Too many requested 0-0 edges for G."
        )

    rare_00_edges = []

    for i in range(G_NUM_RARE_00_EDGES):

        u = rare_vertices[2 * i]
        v = rare_vertices[2 * i + 1]

        edge = (
            min(u, v),
            max(u, v)
        )

        edges.add(edge)
        rare_00_edges.append(edge)

    save_graph(
        DATASET_DIR / "G.json",
        colors,
        edges
    )

    print("======================================")
    print("Background G created")
    print("======================================")

    print(
        f"Vertices: {len(colors)}"
    )

    print(
        f"Color 0 vertices: "
        f"{G_NUM_COLOR_0}"
    )

    print(
        f"Color 1 vertices: "
        f"{G_NUM_COLOR_1}"
    )

    print(
        f"Total edges: "
        f"{len(edges)}"
    )

    print(
        f"Rare 0-0 edges: "
        f"{len(rare_00_edges)}"
    )

    print(
        "0-0-0 triangles: 0 "
        "(guaranteed by matching construction)"
    )

    print()


# ============================================================
# Query S_i
# ============================================================

def generate_queries():

    ground_truth = {}

    for i in range(1, N_QUERIES + 1):

        (
            colors,
            edges,
            color_0_vertices,
            _
        ) = generate_connected_bipartite_graph(
            S_NUM_COLOR_0,
            S_NUM_COLOR_1,
            TARGET_AVG_DEGREE
        )

        # ----------------------------------------------------
        # Plant the rare 0-0-0 triangle
        # ----------------------------------------------------
        #
        # There are exactly three color-0 vertices in S_i.
        #
        # Connect:
        #
        #       u
        #      / \
        #     v---w
        #
        # All three vertices have color 0.
        # ----------------------------------------------------

        if len(color_0_vertices) != 3:
            raise RuntimeError(
                "S_i must contain exactly 3 color-0 vertices."
            )

        u, v, w = color_0_vertices

        triangle_edges = [
            (
                min(u, v),
                max(u, v)
            ),
            (
                min(u, w),
                max(u, w)
            ),
            (
                min(v, w),
                max(v, w)
            )
        ]

        for edge in triangle_edges:
            edges.add(edge)

        save_graph(
            S_DIR / f"S_{i}.json",
            colors,
            edges
        )

        # Ground truth:
        # these are the three vertices forming
        # the planted 0-0-0 triangle.
        ground_truth[str(i)] = [
            u,
            v,
            w
        ]

        if i % 100 == 0:
            print(
                f"Generated {i}/{N_QUERIES} "
                f"query graphs"
            )

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
    print("======================================")
    print("Unique triangle dataset finished")
    print("======================================")

    print(
        f"Query graphs: {N_QUERIES}"
    )

    print(
        f"Each S_i: "
        f"{S_NUM_COLOR_0 + S_NUM_COLOR_1} vertices"
    )

    print(
        f"Color 0: {S_NUM_COLOR_0}"
    )

    print(
        f"Color 1: {S_NUM_COLOR_1}"
    )

    print(
        "Each S_i contains exactly one "
        "0-0-0 triangle."
    )


# ============================================================
# Main
# ============================================================

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
