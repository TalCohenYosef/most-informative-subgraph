#!/usr/bin/env python3
"""Build the recovered 2x2 toy-model and recovery-rate figure."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import deque
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import Rectangle


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
DATA_ROOT = REPOSITORY_ROOT / "data" / "generated" / "toy_models"
RESULTS_ROOT = REPOSITORY_ROOT / "data" / "results" / "toy"
DEFAULT_PNG = HERE / "figure_02.png"
COLORS = {0: "#6c9bd2", 1: "#f28e52", 2: "#61b27d", 3: "#b279c7"}
EDGE_COLOR = "#111111"
RING_COLOR = "#d62728"
# UNVERIFIED: These recovered values were embedded in the original plotting
# script. They remain unchanged pending recovery of authoritative result files.
KNOWN_RECOVERY = {
    "unique_color": [1.0],
    "unique_pair": [0.0, 1.0, 0.816, 0.935, 0.988, 0.991, 0.997, 0.997],
    "unique_triangle": [0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
}


def read_graph(path: Path) -> tuple[nx.Graph, dict[int, int]]:
    data = json.loads(path.read_text())
    graph = nx.Graph()
    colors = {}
    for item in data["nodes"]:
        node = int(item["id"])
        graph.add_node(node)
        colors[node] = int(item["color"])
    graph.add_edges_from(
        (int(edge["source"]), int(edge["target"])) for edge in data["links"]
    )
    return graph, colors


def read_ground_truth(path: Path) -> list[int]:
    return [int(node) for node in json.loads(path.read_text())["1"]]


def bfs_sample(graph: nx.Graph, seeds: Iterable[int], limit: int) -> list[int]:
    selected = set(seeds)
    queue = deque(seeds)
    while queue and len(selected) < limit:
        node = queue.popleft()
        for neighbor in sorted(
            graph.neighbors(node), key=lambda item: (-graph.degree(item), item)
        ):
            if neighbor not in selected:
                selected.add(neighbor)
                queue.append(neighbor)
                if len(selected) == limit:
                    break
    if len(selected) < limit:
        selected.update(sorted(set(graph) - selected)[: limit - len(selected)])
    return sorted(selected)


def background_sample(
    graph: nx.Graph, colors: dict[int, int], case: str
) -> list[int]:
    if case == "color":
        best_nodes = []
        best_edges = -1
        for seed in sorted(graph, key=lambda node: (-graph.degree(node), node))[:500]:
            nodes = bfs_sample(graph, [seed], 20)
            edge_count = graph.subgraph(nodes).number_of_edges()
            if edge_count > best_edges:
                best_nodes, best_edges = nodes, edge_count
        return best_nodes
    if case == "pair":
        average = sum(dict(graph.degree()).values()) / graph.number_of_nodes()
        seed = min(
            graph,
            key=lambda node: (
                abs(graph.degree(node) - average),
                -graph.degree(node),
                node,
            ),
        )
        return bfs_sample(graph, [seed], 16)

    blue = [node for node in graph if colors[node] == 0]
    rare_edges = [
        (u, v)
        for u, v in graph.edges()
        if colors.get(u) == 0 and colors.get(v) == 0
    ]
    selected_blue = list(rare_edges[0]) if rare_edges else []
    selected_blue += [
        node
        for node in sorted(blue, key=lambda item: (-graph.degree(item), item))
        if node not in selected_blue
    ][: 5 - len(selected_blue)]
    selected = set(selected_blue)
    for node in selected_blue:
        orange = [v for v in sorted(graph.neighbors(node)) if colors.get(v) == 1]
        selected.update(orange[:3])
    return sorted(selected)


def query_sample(
    graph: nx.Graph,
    colors: dict[int, int],
    special: list[int],
    case: str,
    limit: int = 14,
) -> list[int]:
    if case != "triangle":
        return bfs_sample(graph, special, limit)
    seeds = list(special)
    seeds += [
        node
        for node in sorted(graph)
        if colors.get(node) == 0 and node not in seeds
    ][:2]
    orange = {
        neighbor
        for node in seeds
        for neighbor in graph.neighbors(node)
        if colors.get(neighbor) == 1
    }
    ordered = sorted(orange, key=lambda node: (-graph.degree(node), node))
    return sorted(set(seeds + ordered[: limit - len(seeds)]))


def special_edges(
    graph: nx.Graph, special: set[int], case: str
) -> set[tuple[int, int]]:
    if case == "pair" and len(special) == 2:
        u, v = sorted(special)
        return {(u, v)} if graph.has_edge(u, v) else set()
    if case == "triangle" and len(special) == 3:
        nodes = sorted(special)
        return {
            (min(u, v), max(u, v))
            for index, u in enumerate(nodes)
            for v in nodes[index + 1 :]
            if graph.has_edge(u, v)
        }
    return set()


def draw_graph(
    ax: plt.Axes,
    graph: nx.Graph,
    colors: dict[int, int],
    case: str,
    special: Iterable[int] = (),
    seed: int = 1,
    visual_scale: float = 0.78,
) -> None:
    special = set(special)
    if case == "triangle" and len(special) == 3:
        nodes = sorted(special)
        for index, u in enumerate(nodes):
            for v in nodes[index + 1 :]:
                graph.add_edge(u, v)

    if case == "triangle":
        left = sorted(node for node in graph if colors.get(node) == 0)
        right = sorted(node for node in graph if colors.get(node) == 1)
        pos = {
            node: (0.18, 1 - (index + 1) / (len(left) + 1))
            for index, node in enumerate(left)
        }
        pos.update(
            {
                node: (0.82, 1 - (index + 1) / (len(right) + 1))
                for index, node in enumerate(right)
            }
        )
        for node, location in zip(
            sorted(special), [(0.12, 0.68), (0.30, 0.68), (0.21, 0.46)]
        ):
            pos[node] = location
    else:
        pos = nx.spring_layout(
            graph,
            seed=seed,
            k=0.9 / math.sqrt(max(1, graph.number_of_nodes())),
            iterations=120,
        )

    highlighted = special_edges(graph, special, case)
    ordinary = [
        edge for edge in graph.edges() if (min(edge), max(edge)) not in highlighted
    ]
    thick = [edge for edge in graph.edges() if (min(edge), max(edge)) in highlighted]

    # Thin only the displayed Unique-triangle query. Preserve the planted
    # triangle and connectivity; the underlying graph data is not modified.
    if case == "triangle" and len(special) == 3:
        display_graph = graph.copy()
        target_ordinary_edges = 16
        removable = sorted(
            ordinary,
            key=lambda edge: (
                graph.degree(edge[0]) + graph.degree(edge[1]),
                min(edge),
                max(edge),
            ),
            reverse=True,
        )
        kept = {(min(edge), max(edge)) for edge in ordinary}
        for edge in removable:
            if len(kept) <= target_ordinary_edges:
                break
            display_graph.remove_edge(*edge)
            if nx.is_connected(display_graph):
                kept.remove((min(edge), max(edge)))
            else:
                display_graph.add_edge(*edge)
        ordinary = [
            edge for edge in ordinary if (min(edge), max(edge)) in kept
        ]
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edgelist=ordinary,
        edge_color=EDGE_COLOR,
        width=1.8 * visual_scale,
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edgelist=thick,
        edge_color=EDGE_COLOR,
        width=5.0 * visual_scale,
    )
    nx.draw_networkx_nodes(
        graph,
        pos,
        ax=ax,
        node_color=[COLORS.get(colors.get(node), "#999999") for node in graph],
        node_size=230 * visual_scale,
        edgecolors=[RING_COLOR if node in special else EDGE_COLOR for node in graph],
        linewidths=[(2.6 if node in special else 0.7) * visual_scale for node in graph],
    )
    ax.set_axis_off()


def add_case_panel(fig: plt.Figure, cell, case_data) -> None:
    case, title, background_text, query_text, background, query, special, seed = case_data
    x, y, width, height = cell
    outer = fig.add_axes(cell)
    outer.set_axis_off()
    outer.add_patch(
        Rectangle(
            (0, 0),
            1,
            1.075,
            transform=outer.transAxes,
            clip_on=False,
            facecolor="white",
            edgecolor="#c7c7c7",
            linewidth=0.8,
        )
    )
    fig.text(
        x + width / 2,
        y + height * 1.015,
        title,
        ha="center",
        va="top",
        fontsize=18,
        weight="bold",
        zorder=5,
    )
    k_star = {"color": 1, "pair": 2, "triangle": 3}[case]
    outer.text(
        0.5, 0.875, rf"$k^* = {k_star}$", ha="center", fontsize=14, weight="bold"
    )
    outer.text(
        0.25, 0.815, background_text, ha="center", fontsize=12, weight="bold"
    )
    outer.text(0.75, 0.815, query_text, ha="center", fontsize=12, weight="bold")
    left_ax = outer.inset_axes([0.055, 0.075, 0.39, 0.62])
    right_ax = outer.inset_axes([0.555, 0.075, 0.39, 0.62])
    draw_graph(left_ax, *background, case=case, seed=seed)
    draw_graph(right_ax, *query, case=case, special=special, seed=seed + 1)


def recovery_values() -> dict[str, list[float]]:
    measured = {}
    for name in KNOWN_RECOVERY:
        values = []
        paths = sorted(
            (RESULTS_ROOT / name).glob("k_*/summary.csv"),
            key=lambda path: int(path.parent.name.split("_")[1]),
        )
        for path in paths:
            with path.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            if rows:
                values.append(
                    sum(row.get("status") == "found" for row in rows) / len(rows)
                )
        if values:
            measured[name] = values
    return {
        name: measured.get(name, list(reference))
        for name, reference in KNOWN_RECOVERY.items()
    }


def plot_recovery(ax: plt.Axes, show_title: bool = False) -> None:
    labels = {
        "unique_color": "Unique color",
        "unique_pair": "Unique pair",
        "unique_triangle": "Unique triangle",
    }
    line_colors = {
        "unique_color": "#2f6dcc",
        "unique_pair": "#f07f24",
        "unique_triangle": "#2ca02c",
    }
    for name, values in recovery_values().items():
        ax.plot(
            range(1, len(values) + 1),
            values,
            "o-",
            linewidth=2,
            markersize=4.5,
            color=line_colors[name],
            label=labels[name],
        )
    for k, color in ((1, "#2f6dcc"), (2, "#f07f24"), (3, "#2ca02c")):
        ax.axvline(k, color=color, linestyle=":", linewidth=1.4, alpha=0.55)
        ax.text(
            k,
            1.015,
            rf"$k^*={k}$",
            color=color,
            ha="center",
            va="bottom",
            fontsize=12,
            weight="bold",
            clip_on=True,
        )
    if show_title:
        ax.set_title("Planted-structure recovery", fontsize=17, weight="bold")
    ax.set_xlabel("subgraph-size budget $k$", fontsize=13, weight="bold")
    ax.set_ylabel("Recovery rate $R(k)$", fontsize=13, weight="bold")
    ax.set(xlim=(0.7, 8.3), ylim=(-0.03, 1.08), xticks=range(1, 9))
    ax.grid(alpha=0.22)
    ax.tick_params(labelsize=12)
    for label in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        label.set_fontweight("bold")
    legend = ax.legend(frameon=False, fontsize=10, loc="lower right")
    for label in legend.get_texts():
        label.set_fontweight("bold")


def add_recovery_panel(fig: plt.Figure, cell) -> None:
    x, y, width, height = cell
    fig.text(
        x + width / 2,
        y + height * 1.015,
        "Planted-structure recovery",
        ha="center",
        va="top",
        fontsize=18,
        weight="bold",
    )
    left_pad, right_pad, bottom_pad = 0.039, -0.010, 0.045
    ax = fig.add_axes(
        (
            x + left_pad,
            y + bottom_pad,
            width - left_pad - right_pad,
            height - 0.025 - bottom_pad,
        )
    )
    plot_recovery(ax)


def load_cases():
    specs = (
        ("color", "unique_color", "Unique-color", "Reference: G(1000, 0.003)", "Query: S_i ~ G(30, 0.1)"),
        ("pair", "unique_pair", "Unique-pair", "Reference: G(1000, 0.003)", "Query: S_i ~ G(30, 0.1)"),
        ("triangle", "unique_triangle", "Unique-triangle", "Reference: connected bipartite", "Query: |V(S_i)| = 30"),
    )
    cases = []
    for seed, (case, directory, title, background_text, query_text) in enumerate(specs, 1):
        root = DATA_ROOT / directory
        background_graph, background_colors = read_graph(root / "G.json")
        nodes = background_sample(background_graph, background_colors, case)
        background_graph = background_graph.subgraph(nodes).copy()
        background_colors = {node: background_colors[node] for node in nodes}
        query_graph, query_colors = read_graph(root / "S_graphs" / "S_1.json")
        special = read_ground_truth(root / "ground_truth.json")
        nodes = query_sample(query_graph, query_colors, special, case)
        query_graph = query_graph.subgraph(nodes).copy()
        query_colors = {node: query_colors[node] for node in nodes}
        cases.append(
            (
                case,
                title,
                background_text,
                query_text,
                (background_graph, background_colors),
                (query_graph, query_colors),
                special,
                seed,
            )
        )
    return cases


def build_figure(output_png: Path = DEFAULT_PNG) -> None:
    plt.rcParams.update(
        {"font.weight": "bold", "axes.labelweight": "bold", "axes.titleweight": "bold"}
    )
    fig = plt.figure(figsize=(16, 11.8), facecolor="white")
    left, right, bottom, top = 0.035, 0.965, 0.045, 0.955
    hgap, vgap = 0.022, 0.055
    cell_width = (right - left - hgap) / 2
    cell_height = (top - bottom - vgap) / 2
    cells = (
        (left, bottom + cell_height + vgap, cell_width, cell_height),
        (left + cell_width + hgap, bottom + cell_height + vgap, cell_width, cell_height),
        (left, bottom, cell_width, cell_height),
    )
    for cell, case in zip(cells, load_cases()):
        add_case_panel(fig, cell, case)
    add_recovery_panel(
        fig, (left + cell_width + hgap, bottom, cell_width, cell_height)
    )
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print(f"Saved {output_png}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_PNG)
    return parser.parse_args()


if __name__ == "__main__":
    build_figure(parse_args().output)
