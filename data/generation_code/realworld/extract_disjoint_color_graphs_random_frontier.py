#!/usr/bin/env python3
"""Build connected G and S_i with random-frontier growth from random seeds."""

from __future__ import annotations

import argparse
import csv
import heapq
import json
import random
from collections import deque
from pathlib import Path

import networkx as nx
import torch


DATA_ROOT = Path(__file__).resolve().parents[2]
RAW_REALWORLD_DIR = DATA_ROOT / "raw" / "realworld"
GENERATED_REALWORLD_DIR = DATA_ROOT / "generated" / "realworld"
DATASET_INPUT_FILENAMES = {
    "bookchild": "processed_data.pt",
    "sportsfit": "processed_data.pt",
    "ogbn_arxiv": "processed_data.pt",
}


def load_real_graph(input_path: Path) -> tuple[nx.Graph, dict[int, int]]:
    """Load the real-world graph and map each node to its color."""
    # The input is a trusted PyG Data file; PyTorch 2.6+ requires opting out
    # of weights-only loading for this serialized graph object.
    obj = torch.load(input_path, map_location="cpu", weights_only=False)
    graph = nx.Graph()
    graph.add_nodes_from(range(int(obj.num_nodes)))

    seen_edges: set[tuple[int, int]] = set()
    for source, target in zip(obj.edge_index[0].tolist(), obj.edge_index[1].tolist()):
        source = int(source)
        target = int(target)
        if source == target:
            continue
        edge = (min(source, target), max(source, target))
        if edge in seen_edges:
            continue
        seen_edges.add(edge)
        graph.add_edge(*edge)

    colors = {node: int(color) for node, color in enumerate(obj.y.cpu().tolist())}
    return graph, colors


def canonical_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def build_json_graph(graph: nx.Graph, colors: dict[int, int]) -> dict:
    """Serialize a graph in the exact node/link JSON format the suite expects."""
    ordered_nodes = sorted(graph.nodes())
    id_map = {old_id: new_id for new_id, old_id in enumerate(ordered_nodes)}

    nodes = [{"id": id_map[node_id], "color": int(colors[node_id])}
             for node_id in ordered_nodes]
    unique_edges = {canonical_edge(u, v) for u, v in graph.edges()}
    links = [{"source": id_map[u], "target": id_map[v], "color": 0}
             for u, v in sorted(unique_edges)]
    return {"nodes": nodes, "links": links}


def graph_metrics(graph: nx.Graph, colors: dict[int, int]) -> dict:
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    triangle_count = sum(nx.triangles(graph).values()) // 3
    avg_degree = (2.0 * edge_count) / node_count if node_count else 0.0
    return {
        "nodes": node_count,
        "edges": edge_count,
        "colors": len({int(colors[node]) for node in graph.nodes()}),
        "avg_degree": avg_degree,
        "triangles": triangle_count,
    }


def random_frontier_sample(graph: nx.Graph, available: set[int],
                           target_size: int) -> set[int] | None:
    """Grow a connected sample by choosing random vertices from its frontier."""
    if len(available) < target_size:
        return None
    candidates = tuple(available)
    for _ in range(400):
        seed = random.choice(candidates)
        sample = {seed}
        frontier = {neighbor for neighbor in graph.neighbors(seed)
                    if neighbor in available}
        while len(sample) < target_size and frontier:
            vertex = random.choice(tuple(frontier))
            frontier.remove(vertex)
            if vertex in sample:
                continue
            sample.add(vertex)
            frontier.update(neighbor for neighbor in graph.neighbors(vertex)
                            if neighbor in available and neighbor not in sample)
        if len(sample) == target_size:
            return sample
    return None


def connected_sample(graph: nx.Graph, available: set[int], target_size: int) -> set[int] | None:
    """Grow a connected sample from a uniformly random seed and frontier."""
    return random_frontier_sample(graph, available, target_size)


def path_from_sample_to_color(graph: nx.Graph, sample: set[int],
                              colors: dict[int, int], target_color: int) -> list[int] | None:
    """Find a shortest original-graph path from the sample to a color."""
    queue = deque(sorted(sample))
    parent = {node: None for node in sample}
    target = None
    while queue:
        node = queue.popleft()
        if colors[node] == target_color:
            target = node
            break
        for neighbor in graph.neighbors(node):
            if neighbor not in parent:
                parent[neighbor] = node
                queue.append(neighbor)
    if target is None:
        return None
    path = []
    while target is not None:
        path.append(target)
        target = parent[target]
    return path[::-1]


def find_background_graph(graph: nx.Graph, colors: dict[int, int], min_size: int) -> nx.Graph | None:
    """Grow G from a uniformly random seed, without selecting a hub."""
    largest_component = max(nx.connected_components(graph), key=len)
    component = graph.subgraph(largest_component).copy()
    if component.number_of_nodes() < min_size:
        return None
    sample = random_frontier_sample(component, set(component), min_size)
    if sample is None:
        return None
    # Keep the seed random, but guarantee that final G contains every source
    # color, including very rare colors that random sampling may miss.
    missing_colors = set(colors.values()) - {colors[node] for node in sample}
    for color in sorted(missing_colors):
        path = path_from_sample_to_color(component, sample, colors, color)
        if path is None:
            return None
        sample.update(path)
    subgraph = component.subgraph(sample).copy()
    if subgraph.number_of_edges() <= subgraph.number_of_nodes() - 1:
        return None
    if sum(nx.triangles(subgraph).values()) // 3 == 0:
        return None
    print(f"G random seed: original vertex {min(sample)}, "
          f"initial colors: {len({colors[node] for node in sample})}", flush=True)
    return subgraph


def find_query_graph(graph: nx.Graph, colors: dict[int, int], min_size: int, max_size: int,
                     used_vertices: set[int]) -> nx.Graph | None:
    """Return a connected query graph that is not tree-like and has at least 5 colors."""
    available = set(graph.nodes()) - used_vertices
    if len(available) < min_size:
        return None

    # A query cannot cross components left by the previously assigned vertices.
    available_graph = graph.subgraph(available)
    largest_component = max(nx.connected_components(available_graph), key=len)
    if len(largest_component) < min_size:
        return None

    for _ in range(2000):
        target_size = random.randint(min_size, min(max_size, len(largest_component)))
        sample = connected_sample(graph, largest_component, target_size)
        if sample is None:
            continue
        subgraph = graph.subgraph(sample).copy()
        if not nx.is_connected(subgraph):
            continue
        if len({int(colors[node]) for node in subgraph.nodes()}) < 5:
            continue
        if subgraph.number_of_edges() <= subgraph.number_of_nodes() - 1:
            continue
        if sum(nx.triangles(subgraph).values()) // 3 < 2:
            continue
        return subgraph
    return None


def attach_remaining_vertices(graph: nx.Graph, background: nx.Graph,
                              queries: list[nx.Graph], background_limit: int
                              ) -> tuple[nx.Graph, list[nx.Graph], list[int]]:
    """Grow G to its limit, then balance degree-capped S additions."""
    groups = [background, *queries]
    owner: dict[int, int] = {}
    for group_index, group in enumerate(groups):
        for vertex in group.nodes():
            if vertex in owner:
                raise ValueError(f"Vertex {vertex} was assigned to more than one graph")
            owner[vertex] = group_index

    if len(background) > background_limit:
        raise ValueError("Initial G already exceeds the requested G limit")

    frontier = {neighbor for vertex in background.nodes()
                for neighbor in graph.neighbors(vertex)
                if neighbor not in owner}
    background_size = len(background)
    while frontier and background_size < background_limit:
        vertex = random.choice(tuple(frontier))
        frontier.remove(vertex)
        if vertex in owner:
            continue
        owner[vertex] = 0
        background_size += 1
        frontier.update(neighbor for neighbor in graph.neighbors(vertex)
                        if neighbor not in owner)

    # One new vertex per turn; prefer the S graph with fewest additions so far.
    sources = [deque(random.sample(list(query.nodes()), len(query))) for query in queries]
    neighbor_iters = [None] * len(queries)
    added = [0] * len(queries)
    query_nodes = [len(query) for query in queries]
    query_edges = [query.number_of_edges() for query in queries]
    turns = [(0, index) for index in range(len(queries))]
    heapq.heapify(turns)
    while turns:
        _, index = heapq.heappop(turns)
        claimed = False
        while sources[index]:
            if neighbor_iters[index] is None:
                neighbors = list(graph.neighbors(sources[index][0]))
                random.shuffle(neighbors)
                neighbor_iters[index] = iter(neighbors)
            for neighbor in neighbor_iters[index]:
                if neighbor not in owner:
                    new_edges = sum(owner.get(other) == index + 1
                                    for other in graph.neighbors(neighbor))
                    owner[neighbor] = index + 1
                    sources[index].append(neighbor)
                    added[index] += 1
                    query_nodes[index] += 1
                    query_edges[index] += new_edges
                    heapq.heappush(turns, (added[index], index))
                    claimed = True
                    break
            if claimed:
                break
            sources[index].popleft()
            neighbor_iters[index] = None

    expanded = [nx.Graph() for _ in groups]
    for vertex, group_index in owner.items():
        expanded[group_index].add_node(vertex)
    for source, target in graph.edges():
        source_group = owner.get(source)
        if source_group is not None and source_group == owner.get(target):
            expanded[source_group].add_edge(source, target)

    unassigned = sorted(set(graph.nodes()) - owner.keys())
    return expanded[0], expanded[1:], unassigned


def save_graph_json(path: Path, graph: nx.Graph, colors: dict[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(build_json_graph(graph, colors), handle, separators=(",", ":"))


def save_query_average_degrees(path: Path, queries: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["query", "avg_degree"])
        for query in queries:
            writer.writerow([query["filename"], query["avg_degree"]])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        choices=tuple(DATASET_INPUT_FILENAMES),
        help=("Dataset name. When supplied, input and output default to "
              "data/raw/realworld/<dataset>/processed_data.pt and "
              "data/generated/realworld/<dataset>/"),
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Override the input .pt path (otherwise derived from --dataset)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override the output folder (otherwise derived from --dataset)",
    )
    parser.add_argument("--num-queries", type=int, default=100,
                        help="How many pairwise-disjoint query graphs to generate")
    parser.add_argument("--g-size", type=int, default=10000,
                        help="Initial background graph size")
    parser.add_argument("--g-max-size", type=int, default=7000,
                        help="Maximum final background graph size")
    parser.add_argument("--s-min-size", type=int, default=500,
                        help="Minimum query size")
    parser.add_argument("--s-max-size", type=int, default=1000,
                        help="Maximum query size")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    args = parser.parse_args()
    if args.input is None:
        if args.dataset is None:
            parser.error("Provide --dataset or --input")
        args.input = RAW_REALWORLD_DIR / args.dataset / DATASET_INPUT_FILENAMES[args.dataset]
    if args.output_dir is None:
        if args.dataset is None:
            parser.error("Provide --dataset or --output-dir")
        args.output_dir = GENERATED_REALWORLD_DIR / args.dataset
    if args.g_size < 1 or args.g_max_size < args.g_size:
        parser.error("Require 1 <= g-size <= g-max-size")

    random.seed(args.seed)
    graph, colors = load_real_graph(args.input)

    background = find_background_graph(graph, colors, args.g_size)
    if background is None:
        raise ValueError("Could not build a valid connected background graph G")

    used_vertices = set(background.nodes())
    query_graphs: list[nx.Graph] = []
    for index in range(1, args.num_queries + 1):
        query = find_query_graph(graph, colors, args.s_min_size, args.s_max_size, used_vertices)
        if query is None:
            raise ValueError(f"Could not construct S_{index}")
        used_vertices |= set(query.nodes())
        query_graphs.append(query)
        print(f"Sampled S_{index}: {query.number_of_nodes()} vertices", flush=True)

    background, query_graphs, unassigned = attach_remaining_vertices(
        graph, background, query_graphs, args.g_max_size)
    if {colors[node] for node in background} != set(colors.values()):
        raise ValueError("Final G does not contain every source color")
    for index, output_graph in enumerate([background, *query_graphs]):
        name = "G" if index == 0 else f"S_{index}"
        if output_graph.number_of_nodes() == 0 or not nx.is_connected(output_graph):
            raise ValueError(f"Final graph {name} is not connected")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    queries_dir = output_dir / "queries"
    queries_dir.mkdir(parents=True, exist_ok=True)
    save_graph_json(output_dir / "G.json", background, colors)
    for index, query in enumerate(query_graphs, start=1):
        save_graph_json(queries_dir / f"S_{index}.json", query, colors)

    (output_dir / "unassigned_original_vertex_ids.json").write_text(
        json.dumps(unassigned), encoding="utf-8")

    summary = {
        "background": {"filename": "G.json", **graph_metrics(background, colors)},
        "queries": [{"filename": f"queries/S_{index}.json", **graph_metrics(query, colors)}
                     for index, query in enumerate(query_graphs, start=1)],
        "disjoint_checks": {
            "G_vs_queries_disjoint": all(set(background.nodes()).isdisjoint(set(query.nodes()))
                                         for query in query_graphs),
            "queries_pairwise_disjoint": all(
                set(query_graphs[i].nodes()).isdisjoint(set(query_graphs[j].nodes()))
                for i in range(len(query_graphs))
                for j in range(i + 1, len(query_graphs))
            ),
        },
        "assignment": {
            "total_original_vertices": graph.number_of_nodes(),
            "assigned_vertices": graph.number_of_nodes() - len(unassigned),
            "unassigned_vertices": len(unassigned),
            "unassigned_file": "unassigned_original_vertex_ids.json",
            "background_max_vertices": args.g_max_size,
            "query_expansion": "one reachable unused vertex per turn, prioritizing the S graph with fewest added vertices",
            "note": "Final graph sizes may exceed the requested sample size range.",
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    save_query_average_degrees(output_dir / "S_average_degrees.csv", summary["queries"])

    print(json.dumps({
        "background": summary["background"],
        "num_queries": len(query_graphs),
        "query_sizes": [query.number_of_nodes() for query in query_graphs],
    }, indent=2))


if __name__ == "__main__":
    main()
