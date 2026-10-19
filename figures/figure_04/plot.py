#!/usr/bin/env python3
"""
Create a combined figure with:
1) Main scatter plot of:
   VISTA remaining queries - Graphlets Enumeration remaining queries
   for each pattern size K=1..10

2) Inset stacked bar plot showing percentages of configurations where:
   - VISTA leaves fewer
   - Equal
   - Graphlets Enumeration leaves fewer
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
import result_readers as comparison


# ============================================================
# PATHS
# ============================================================

GRAPHLETS_ROOT = ROOT / "data" / "results" / "graphlets"
PATTERN_ROOT = ROOT / "data" / "results" / "vista" / "case_summaries"

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "figure_04.png"


# ============================================================
# COLORS FOR K = 1..10
# ============================================================

COLORS = (
    "#1f6feb",  # K=1
    "#ff7f0e",  # K=2
    "#22c55e",  # K=3
    "#ef4444",  # K=4
    "#a855f7",  # K=5
    "#a16207",  # K=6
    "#ec4899",  # K=7
    "#06b6d4",  # K=8
    "#3b82f6",  # K=9
    "#6B2D5C",  # K=10 - eggplant purple
)


# ============================================================
# HELPER: BUILD PERCENTAGES FOR INSET
# ============================================================

def build_percentages(series: dict, max_k: int):
    """
    For each K, compute percentages of:
      - VISTA leaves fewer
      - Equal
      - Graphlets Enumeration leaves fewer
    """
    total = len(series)

    vista_pct = []
    equal_pct = []
    graphlet_pct = []

    for k in range(1, max_k + 1):
        vista_fewer = 0
        equal = 0
        graphlet_fewer = 0

        for _, (graphlet_remaining, vista_remaining) in series.items():
            vista_val = vista_remaining[k - 1]

            if vista_val < graphlet_remaining:
                vista_fewer += 1
            elif vista_val > graphlet_remaining:
                graphlet_fewer += 1
            else:
                equal += 1

        vista_pct.append(100.0 * vista_fewer / total)
        equal_pct.append(100.0 * equal / total)
        graphlet_pct.append(100.0 * graphlet_fewer / total)

    return vista_pct, equal_pct, graphlet_pct


# ============================================================
# MAIN
# ============================================================

def main(output_path: Path) -> None:
    max_k = 10

    # --------------------------------------------------------
    # Load matched S/G configuration data
    # Expected format from build_count_series:
    # series[key] = (graphlet_remaining, vista_remaining)
    # where:
    #   graphlet_remaining = scalar
    #   vista_remaining = list/array of length max_k
    # --------------------------------------------------------
    series = comparison.build_count_series(GRAPHLETS_ROOT, PATTERN_ROOT, max_k)

    if not series:
        raise ValueError("No matched S/G configurations found.")

    vista_pct, equal_pct, graphlet_pct = build_percentages(series, max_k)
    k_values = np.arange(1, max_k + 1)

    # --------------------------------------------------------
    # Figure and main axis
    # --------------------------------------------------------
    fig = plt.figure(figsize=(16, 10), facecolor="white")
    ax = fig.add_axes([0.08, 0.10, 0.86, 0.82])

    # --------------------------------------------------------
    # Main scatter plot
    # --------------------------------------------------------
    for k in range(1, max_k + 1):
        differences = []

        for _, (graphlet_remaining, vista_remaining) in series.items():
            diff = vista_remaining[k - 1] - graphlet_remaining
            differences.append(diff)

        differences = np.asarray(differences)

        rng = np.random.default_rng(42 + k)
        jitter = rng.normal(loc=0.0, scale=0.08, size=len(differences))

        ax.scatter(
            np.full(len(differences), k) + jitter,
            differences,
            s=60,
            color=COLORS[k - 1],
            alpha=0.45,
            edgecolors="none",
            zorder=3,
        )

    # Zero line
    ax.axhline(0, color="#26384f", linewidth=2.4, zorder=2)

    # Y axis scale similar to your figure
    ax.set_yscale("symlog", linthresh=1, linscale=1, base=10)

    # Limits
    ax.set_xlim(0.5, max_k + 0.5)
    ax.set_ylim(-1000, 1200)   # <-- updated here

    # Ticks
    ax.set_xticks(k_values)
    ax.set_xticklabels(
        [f"K={k}" for k in k_values],
        fontsize=16,
        fontweight="bold",
    )

    # Color each K label like the points
    for tick, color in zip(ax.get_xticklabels(), COLORS):
        tick.set_color(color)

    # Axis labels only (no title)
    ax.set_xlabel(
        "Pattern size K",
        fontsize=20,
        fontweight="bold",
        labelpad=14,
    )
    ax.set_ylabel(
        "S queries remaining: VISTA - Graphlets Enumeration",
        fontsize=20,
        fontweight="bold",
        labelpad=14,
    )

    # Tick sizes
    ax.tick_params(axis="x", labelsize=16, width=1.2, length=6, pad=8)
    ax.tick_params(axis="y", labelsize=15, width=1.2, length=6)
    for tick in ax.get_yticklabels():
        tick.set_fontweight("bold")

    # Grid
    ax.grid(axis="y", color="#d8e0ea", linewidth=1.2)
    ax.set_axisbelow(True)

    # Spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.2)
    ax.spines["bottom"].set_linewidth(1.2)

    # --------------------------------------------------------
    # Inset stacked bar chart
    # --------------------------------------------------------
    ax_inset = fig.add_axes([0.13, 0.18, 0.36, 0.29], zorder=10)
    ax_inset.set_facecolor("white")

    inset_k = np.arange(1, max_k + 1)
    inset_vista = np.asarray(vista_pct)
    inset_equal = np.asarray(equal_pct)
    inset_graphlet = np.asarray(graphlet_pct)

    # Stacked bars
    ax_inset.bar(
        inset_k,
        inset_vista,
        width=0.78,
        color="#D69A56",
        edgecolor="white",
        linewidth=0.6,
        label="VISTA leaves fewer",
    )

    ax_inset.bar(
        inset_k,
        inset_equal,
        width=0.78,
        bottom=inset_vista,
        color="#E4C58F",
        edgecolor="white",
        linewidth=0.6,
        label="Equal",
    )

    ax_inset.bar(
        inset_k,
        inset_graphlet,
        width=0.78,
        bottom=inset_vista + inset_equal,
        color="#69AABD",
        edgecolor="white",
        linewidth=0.6,
        label="Graphlets Enumeration leaves fewer",
    )

    # Inset limits and ticks
    ax_inset.set_xlim(0.4, 10.6)
    ax_inset.set_ylim(0, 100)

    ax_inset.set_xticks(inset_k)
    ax_inset.set_xticklabels(
        [f"K={k}" for k in inset_k], fontsize=8, fontweight="bold"
    )

    ax_inset.set_yticks(np.arange(0, 101, 20))
    ax_inset.set_yticklabels(
        [f"{y}%" for y in range(0, 101, 20)], fontsize=8, fontweight="bold"
    )

    # Inset axis labels only
    ax_inset.set_xlabel(
        "Pattern size K",
        fontsize=9,
        fontweight="bold",
        labelpad=4,
    )
    ax_inset.set_ylabel(
        "Configurations (%)",
        fontsize=9,
        fontweight="bold",
        labelpad=4,
    )

    ax_inset.grid(axis="y", color="#d4d9df", linewidth=0.7, alpha=0.7)
    ax_inset.set_axisbelow(True)

    # Frame for inset
    for spine in ax_inset.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.9)
        spine.set_color("#9ca3af")

    # Legend under inset - moved a bit up
    ax_inset.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),   # <-- moved upward
        ncol=3,
        frameon=False,
        prop={"size": 7.5, "weight": "bold"},
        columnspacing=1.1,
        handlelength=1.7,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Saved: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args().output)
