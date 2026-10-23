#!/usr/bin/env python3
"""Generate manuscript Figure 3 from the saved compact result files.

The Graphlets panel intentionally preserves the paper calculation: for each
degree pair it displays the maximum survival percentage across the nine
query/reference color-distribution pairs.  This is not a pooled average.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize, SymLogNorm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures" / "analysis"))

import result_readers
from figure_03_vista_panel import CONFIGURATIONS, LAPAZ, build_matrices, read_summaries

VISTA_INPUT = ROOT / "data" / "results" / "vista" / "synthetic_summaries"
GRAPHLETS_INPUT = ROOT / "data" / "results" / "graphlets"
REALWORLD_INPUT = ROOT / "data" / "results" / "realworld"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "figure_03.png"

DEGREES = (3, 5, 8, 15)
SHORT = {"average": "A", "rare": "R", "uniform": "U"}
AXIS_TICK_SIZE = 12
AXIS_LABEL_SIZE = 18
PANEL_TITLE_SIZE = 18
DATA_LABEL_SIZE = 14
LOWER_AXIS_TICK_SIZE = 16
LOWER_AXIS_LABEL_SIZE = AXIS_LABEL_SIZE


def graphlets_degree_maxima() -> np.ndarray:
    """Return maximum query-survival percentage for every degree pair."""
    results = result_readers.read_graphlets(GRAPHLETS_INPUT)
    if len(results) != 144:
        raise ValueError(f"Expected 144 Graphlets configurations; found {len(results)}")
    matrix = np.zeros((4, 4), dtype=float)
    for row, query_degree in enumerate(DEGREES):
        for column, reference_degree in enumerate(DEGREES):
            percentages = []
            for (_, s_degree, _, g_degree), (values, _) in results.items():
                if s_degree == query_degree and g_degree == reference_degree:
                    percentages.append(
                        100.0 * sum(value == 0 for value in values.values()) / len(values)
                    )
            if len(percentages) != 9:
                raise ValueError(
                    f"Expected nine color pairs for ({query_degree}, {reference_degree}); "
                    f"found {len(percentages)}"
                )
            matrix[row, column] = max(percentages)
    return matrix


def realworld_curves() -> dict[str, list[int]]:
    datasets = {
        "BookChild": "bookchild",
        "SportsFit": "sportsfit",
        "OGBN-Arxiv": "ogbn_arxiv",
    }
    curves = {}
    for label, directory in datasets.items():
        path = REALWORLD_INPUT / directory / "recovery_results" / "first_not_found.csv"
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 100:
            raise ValueError(f"Expected 100 real-world queries in {path}; found {len(rows)}")
        first_absent = [int(row["first_not_found_size"]) for row in rows]
        curves[label] = [sum(value > k for value in first_absent) for k in range(11)]
    return curves


def main(output_path: Path) -> None:
    summaries = read_summaries(VISTA_INPUT)
    matrices = build_matrices(summaries, 10)
    graphlet_matrix = graphlets_degree_maxima()
    curves = realworld_curves()

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 14,
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.titleweight": "bold",
        }
    )
    # Chosen to match the saved manuscript composite's 6292 x 3685 canvas
    # after tight bounding-box cropping at 300 dpi.
    fig = plt.figure(figsize=(22.04, 12.88), facecolor="white")
    outer = fig.add_gridspec(2, 1, height_ratios=(2.05, 1.0), hspace=0.32)
    top = outer[0].subgridspec(
        2,
        7,
        width_ratios=(1, 1, 1, 1, 1, 0.12, 0.48),
        wspace=0.07,
        hspace=0.30,
    )
    labels = [f"{SHORT[family]}\n{degree}" for family, degree in CONFIGURATIONS]
    heatmap_image = None
    lower_heatmap_axes = []
    for index, (k, matrix) in enumerate(matrices.items()):
        axis = fig.add_subplot(top[index // 5, index % 5])
        if index >= 5:
            lower_heatmap_axes.append(axis)
        heatmap_image = axis.imshow(
            matrix,
            cmap=LAPAZ,
            norm=SymLogNorm(linthresh=1, vmin=0, vmax=1000, base=10),
            aspect="auto",
        )
        axis.set_title(f"k = {k}", fontsize=PANEL_TITLE_SIZE, fontweight="bold", pad=10)
        axis.set_xticks(range(12), labels=labels)
        axis.set_yticks(
            range(12),
            labels=[f"{SHORT[family]} {degree}" for family, degree in CONFIGURATIONS],
        )
        axis.tick_params(axis="x", labelsize=AXIS_TICK_SIZE, length=0, pad=5)
        axis.tick_params(axis="y", labelsize=AXIS_TICK_SIZE, length=0, pad=5)
        if index % 5 != 0:
            axis.tick_params(labelleft=False)
        for label in [*axis.get_xticklabels(), *axis.get_yticklabels()]:
            label.set_fontweight("bold")
        axis.set_xticks(np.arange(-0.5, 12, 1), minor=True)
        axis.set_yticks(np.arange(-0.5, 12, 1), minor=True)
        axis.grid(which="minor", color="white", linewidth=0.8, alpha=0.9)
        axis.tick_params(which="minor", bottom=False, left=False)
        for boundary in (3.5, 7.5):
            axis.axvline(boundary, color="white", linewidth=1.8)
            axis.axhline(boundary, color="white", linewidth=1.8)
        for spine in axis.spines.values():
            spine.set_color("#475569")
            spine.set_linewidth(0.7)
    for axis in lower_heatmap_axes:
        axis.set_position(axis.get_position().translated(0, -0.01))
    color_axis = fig.add_subplot(top[:, 5])
    colorbar = fig.colorbar(
        heatmap_image, cax=color_axis, ticks=(0, 1, 10, 100, 1000)
    )
    colorbar.set_label(
        "Non-negated queries", fontsize=AXIS_LABEL_SIZE, fontweight="bold", labelpad=10
    )
    colorbar.ax.tick_params(labelsize=AXIS_TICK_SIZE)
    fig.text(
        0.5,
        0.37,
        "Reference graph configuration, G",
        ha="center",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
    )
    fig.text(
        0.025,
        0.70,
        "Query configuration, S",
        rotation=90,
        va="center",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
    )
    fig.text(
        0.84,
        0.92,
        "A = Average\nR = Rare\nU = Uniform",
        ha="center",
        va="top",
        fontsize=16,
        fontweight="bold",
        multialignment="center",
        linespacing=1.25,
        bbox={
            "boxstyle": "round,pad=0.3",
            "facecolor": "#F7FAFC",
            "edgecolor": "#8292A3",
        },
    )

    bottom = outer[1].subgridspec(1, 2, width_ratios=(1.0, 1.25), wspace=0.22)
    graphlet_axis = fig.add_subplot(bottom[0, 0])
    graphlet_image = graphlet_axis.imshow(
        graphlet_matrix,
        cmap=LAPAZ,
        norm=Normalize(vmin=0, vmax=max(21.5, float(graphlet_matrix.max()))),
        aspect="auto",
    )
    graphlet_axis.set_xticks(
        range(4), labels=[rf"$d_G = {degree}$" for degree in DEGREES]
    )
    graphlet_axis.set_yticks(
        range(4), labels=[rf"$d_S = {degree}$" for degree in DEGREES]
    )
    graphlet_axis.tick_params(axis="both", labelsize=LOWER_AXIS_TICK_SIZE, length=0)
    graphlet_axis.set_xlabel(
        "Reference graph G", fontsize=LOWER_AXIS_LABEL_SIZE, fontweight="bold"
    )
    graphlet_axis.set_ylabel(
        "Query graph library S",
        fontsize=LOWER_AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=0,
    )
    graphlet_axis.yaxis.label.set_y(0.5)
    for row in range(4):
        for column in range(4):
            value = graphlet_matrix[row, column]
            if value > 0:
                graphlet_axis.text(
                    column,
                    row,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=DATA_LABEL_SIZE,
                    fontweight="bold",
                    color="white" if value > 10 else "black",
                )
    graphlet_colorbar = fig.colorbar(
        graphlet_image, ax=graphlet_axis, orientation="horizontal", pad=0.20
    )
    graphlet_colorbar.ax.tick_params(labelsize=LOWER_AXIS_TICK_SIZE)

    real_axis = fig.add_subplot(bottom[0, 1])
    real_axis.set_facecolor("white")
    colors = {"BookChild": "#D69A56", "SportsFit": "#78A5A3", "OGBN-Arxiv": "#4B8FA8"}
    for label, values in curves.items():
        real_axis.plot(
            range(11),
            values,
            marker="o",
            markersize=4,
            linewidth=1.8,
            label=label,
            color=colors[label],
        )
    real_axis.set_xlabel("k", fontsize=LOWER_AXIS_LABEL_SIZE, fontweight="bold")
    real_axis.set_ylabel(
        "S queries remaining", fontsize=LOWER_AXIS_LABEL_SIZE, fontweight="bold"
    )
    real_axis.yaxis.label.set_y(0.5)
    real_axis.set_xticks(range(11))
    real_axis.tick_params(axis="both", labelsize=LOWER_AXIS_TICK_SIZE)
    real_axis.set_ylim(0, 102)
    real_axis.grid(color="#E5E1D8", linewidth=0.7)
    real_axis.legend(frameon=False, fontsize=16, loc="upper right")

    fig.subplots_adjust(left=0.065, right=0.89, top=0.95, bottom=0.075)
    color_axis.set_position((0.80, 0.46, 0.018, 0.34))
    graphlet_axis.set_position(graphlet_axis.get_position().translated(0.02, 0))
    graphlet_colorbar.ax.set_position(
        graphlet_colorbar.ax.get_position().translated(0.02, 0)
    )
    shared_y = real_axis.get_position().y0 + real_axis.get_position().height / 2
    for axis, label_x in ((graphlet_axis, -0.14), (real_axis, -0.07)):
        axis_position = axis.get_position()
        label_y = (shared_y - axis_position.y0) / axis_position.height
        axis.yaxis.set_label_coords(label_x, label_y)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")
    print(f"Saved: {output_path.with_suffix('.pdf')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args().output)
