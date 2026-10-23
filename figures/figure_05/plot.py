#!/usr/bin/env python3
"""Create a combined timing and negation-score comparison figure.

The script reads:
- graphlet_preprocessing_timings.csv
- graphlet_case_timings.csv
- all first_not_found_timings.csv files under recovery_results_pattern_finder

It aggregates the timing data by case family and combines it with a heatmap of
the theoretical negation score versus the cumulative fraction negated.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm
import numpy as np
import pandas as pd


SCRIPT_ROOT = Path(__file__).resolve().parent
ROOT = SCRIPT_ROOT.parents[1]
PATTERN_ROOT = ROOT / "data" / "results" / "vista" / "timings"
GRAPHLET_PREPROCESSING = (
    ROOT / "data" / "results" / "graphlets" / "timings" / "graphlet_preprocessing_timings.csv"
)
GRAPHLET_CASES = (
    ROOT / "data" / "results" / "graphlets" / "timings" / "graphlet_case_timings.csv"
)
THEORY_RESULTS = (
    ROOT
    / "data"
    / "results"
    / "theory"
    / "detailed_configuration_results.csv"
)
DEFAULT_OUTPUT = SCRIPT_ROOT / "figure_05.png"

CASE_ORDER = [
    "average_deg_3",
    "average_deg_5",
    "average_deg_8",
    "average_deg_15",
    "rare_deg_3",
    "rare_deg_5",
    "rare_deg_8",
    "rare_deg_15",
    "uniform_deg_3",
    "uniform_deg_5",
    "uniform_deg_8",
    "uniform_deg_15",
]

AXIS_LABEL_SIZE = 17
AXIS_TICK_SIZE = 14
LEGEND_SIZE = 14
HEATMAP_HEIGHT_SCALE = 0.9


def normalize_pattern_case_name(path: Path) -> str:
    """Return the query family containing this S-family/G-family run."""
    name = path.parent.parent.name
    prefix = "results_queris_"
    if not name.startswith(prefix):
        raise ValueError(f"Unexpected query-family folder: {name}")
    return name[len(prefix):]


def load_pattern_summary() -> pd.DataFrame:
    frames = []
    for csv_path in sorted(PATTERN_ROOT.glob("**/first_not_found_timings.csv")):
        df = pd.read_csv(csv_path)
        df["case"] = normalize_pattern_case_name(csv_path)
        frames.append(df[["case", "pattern_generation_seconds", "graph_search_seconds"]])

    if not frames:
        raise FileNotFoundError(f"No pattern timing CSV files found under: {PATTERN_ROOT}")

    summary = pd.concat(frames, ignore_index=True)
    summary = summary.groupby("case", as_index=False).agg(
        VISTA_PREP=("pattern_generation_seconds", "sum"),
        VISTA_SEARCH=("graph_search_seconds", "sum"),
    )
    # Keep TOTAL exactly consistent with the two components shown in the plots.
    summary["VISTA_TOTAL"] = summary["VISTA_PREP"] + summary["VISTA_SEARCH"]
    return summary


def load_graphlet_summary() -> pd.DataFrame:
    preprocessing = pd.read_csv(GRAPHLET_PREPROCESSING)
    preprocessing = preprocessing[["query_family", "preprocessing_seconds"]].rename(
        columns={"query_family": "case", "preprocessing_seconds": "GRAPHLET_PREP"}
    )

    cases = pd.read_csv(GRAPHLET_CASES)
    cases = cases[["query_family", "filtering_seconds"]].rename(
        columns={"query_family": "case"}
    )
    searches = cases.groupby("case", as_index=False).agg(
        GRAPHLET_SEARCH=("filtering_seconds", "sum"),
    )

    summary = preprocessing.merge(searches, on="case", how="inner")
    summary["GRAPHLET_TOTAL"] = summary["GRAPHLET_PREP"] + summary["GRAPHLET_SEARCH"]
    return summary


def load_negation_heatmap() -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray
]:
    """Bin all results and the two extreme cumulative-negation groups."""
    theory = pd.read_csv(THEORY_RESULTS)
    required = {"mean_negation_score", "cumulative_negation_rate"}
    missing = required.difference(theory.columns)
    if missing:
        raise ValueError(f"Missing theory-result columns: {sorted(missing)}")

    scores = theory["mean_negation_score"].to_numpy()
    fractions = theory["cumulative_negation_rate"].to_numpy()
    heatmap, score_edges, fraction_edges = np.histogram2d(
        scores, fractions, bins=(10, 10)
    )
    low_fraction_counts, _ = np.histogram(
        scores[fractions <= 0.05], bins=score_edges
    )
    high_fraction_counts, _ = np.histogram(
        scores[fractions >= 0.95], bins=score_edges
    )
    return (
        heatmap.T,
        score_edges,
        fraction_edges,
        low_fraction_counts,
        high_fraction_counts,
    )


def main(output_path: Path) -> None:
    pattern = load_pattern_summary()
    graphlets = load_graphlet_summary()

    combined = pattern.merge(graphlets, on="case", how="inner")
    combined = combined.set_index("case").reindex(CASE_ORDER).reset_index().rename(columns={"case": "Case"})

    if combined["Case"].isna().any():
        missing = [case for case in CASE_ORDER if case not in combined["Case"].tolist()]
        raise ValueError(f"Missing benchmark cases: {missing}")

    for method in ("VISTA", "GRAPHLET"):
        expected_total = combined[f"{method}_PREP"] + combined[f"{method}_SEARCH"]
        if not expected_total.equals(combined[f"{method}_TOTAL"]):
            raise ValueError(f"{method}_TOTAL is not PREP + SEARCH")

    # Values are amortized over 1,000 queries x 12 backgrounds.
    x = range(len(CASE_ORDER))
    width = 0.35
    comparisons_per_family = 12_000
    (
        heatmap,
        score_edges,
        fraction_edges,
        low_fraction_counts,
        high_fraction_counts,
    ) = load_negation_heatmap()
    fig = plt.figure(figsize=(18, 12.5))
    grid = fig.add_gridspec(
        2, 2, height_ratios=(1.0, 0.9), width_ratios=(1.08, 1.0)
    )
    ax = fig.add_subplot(grid[0, :])
    heat_ax = fig.add_subplot(grid[1, 0])
    extreme_ax = fig.add_subplot(grid[1, 1])
    x_values = list(x)
    vista_x = [i - width / 2 for i in x_values]
    graphlet_x = [i + width / 2 for i in x_values]

    vista_prep = combined["VISTA_PREP"].to_numpy() / comparisons_per_family
    vista_search = combined["VISTA_SEARCH"].to_numpy() / comparisons_per_family
    graphlet_prep = combined["GRAPHLET_PREP"].to_numpy() / comparisons_per_family
    graphlet_search = combined["GRAPHLET_SEARCH"].to_numpy() / comparisons_per_family

    ax.bar(
        vista_x, vista_prep, width=width, label="VISTA — preprocessing",
        color="#69AABD", edgecolor="white", linewidth=0.7,
    )
    ax.bar(
        vista_x, vista_search, width=width, bottom=vista_prep,
        label="VISTA — searching", color="#78A5A3",
        edgecolor="white", linewidth=0.7,
    )
    ax.bar(
        graphlet_x, graphlet_prep, width=width, label="Graphlets Enumeration — preprocessing",
        color="#D69A56", edgecolor="white", linewidth=0.7,
    )
    ax.bar(
        graphlet_x, graphlet_search, width=width, bottom=graphlet_prep,
        label="Graphlets Enumeration — searching", color="#E4C58F",
        edgecolor="white", linewidth=0.7,
    )

    ax.set_xticks(x_values)
    ax.set_xticklabels(
        [label.replace("_deg_", "\n").title() for label in CASE_ORDER],
        rotation=0, fontsize=AXIS_TICK_SIZE, fontweight="bold",
    )
    ax.set_xlabel(
        "Query configuration", fontsize=AXIS_LABEL_SIZE, fontweight="bold", labelpad=10,
    )
    ax.set_ylabel(
        r"Mean time for one $S_i$–$G$ pair (seconds)",
        fontsize=AXIS_LABEL_SIZE, fontweight="bold", labelpad=10,
    )
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 3.0)
    ax.tick_params(axis="y", labelsize=AXIS_TICK_SIZE)
    for tick in ax.get_yticklabels():
        tick.set_fontweight("bold")
    ax.grid(axis="y", color="#D7DCE2", linewidth=0.8, alpha=0.75)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        ncol=4, frameon=False, loc="lower center",
        bbox_to_anchor=(0.5, 1.08), prop={"size": LEGEND_SIZE, "weight": "bold"},
        columnspacing=1.5,
    )

    score_centers = (score_edges[:-1] + score_edges[1:]) / 2
    fraction_centers = (fraction_edges[:-1] + fraction_edges[1:]) / 2
    timing_cmap = LinearSegmentedColormap.from_list(
        "timing_colors",
        [
            "#69AABD",
            "#8FC5D2",
            "#A8C8B5",
            "#C9D8B6",
            "#E4C58F",
            "#D69A56",
            "#C98A58",
        ],
    )
    heat_image = heat_ax.imshow(
        heatmap,
        cmap=timing_cmap,
        norm=LogNorm(vmin=1, vmax=float(heatmap.max()), clip=True),
        aspect="auto",
        interpolation="nearest",
    )
    heat_ax.set_xticks(range(10), labels=[f"{value:.2f}" for value in score_centers])
    heat_ax.set_yticks(range(10), labels=[f"{value:.2f}" for value in fraction_centers])
    heat_ax.tick_params(axis="x", labelrotation=45)
    plt.setp(heat_ax.get_xticklabels(), ha="right", rotation_mode="anchor")
    heat_ax.set_xlabel(
        "Negation score", fontsize=AXIS_LABEL_SIZE, fontweight="bold", labelpad=2
    )
    heat_ax.set_ylabel(
        "Fraction negated", fontsize=AXIS_LABEL_SIZE, fontweight="bold", labelpad=10
    )
    heat_ax.tick_params(
        axis="both", labelsize=AXIS_TICK_SIZE, direction="in", top=True, right=True
    )
    for tick in (*heat_ax.get_xticklabels(), *heat_ax.get_yticklabels()):
        tick.set_fontweight("bold")

    colorbar = fig.colorbar(heat_image, ax=heat_ax, pad=0.018, fraction=0.028)
    colorbar.set_label(
        r"Configuration–$K$ pairs", fontsize=AXIS_LABEL_SIZE, fontweight="bold", labelpad=10
    )
    colorbar.ax.tick_params(labelsize=AXIS_TICK_SIZE)
    for tick in colorbar.ax.get_yticklabels():
        tick.set_fontweight("bold")

    extreme_x = score_centers
    score_bin_width = score_edges[1] - score_edges[0]
    extreme_width = score_bin_width * 0.38
    extreme_ax.bar(
        extreme_x - extreme_width / 2,
        low_fraction_counts,
        width=extreme_width,
        color="#69AABD",
        edgecolor="white",
        linewidth=0.7,
        label=r"Fraction negated $\leq 0.05$",
    )
    extreme_ax.bar(
        extreme_x + extreme_width / 2,
        high_fraction_counts,
        width=extreme_width,
        color="#C98A58",
        edgecolor="white",
        linewidth=0.7,
        label=r"Fraction negated $\geq 0.95$",
    )
    extreme_ax.set_xlim(score_edges[0], score_edges[-1])
    extreme_ax.set_xticks(np.arange(-5, 46, 5))
    extreme_ax.set_xlabel(
        "Negation score", fontsize=AXIS_LABEL_SIZE, fontweight="bold", labelpad=8
    )
    extreme_ax.tick_params(axis="both", labelsize=AXIS_TICK_SIZE)
    for tick in (*extreme_ax.get_xticklabels(), *extreme_ax.get_yticklabels()):
        tick.set_fontweight("bold")
    extreme_ax.grid(axis="y", color="#D7DCE2", linewidth=0.8, alpha=0.75)
    extreme_ax.set_axisbelow(True)
    extreme_ax.spines["top"].set_visible(False)
    extreme_ax.spines["right"].set_visible(False)
    extreme_ax.legend(
        frameon=False, prop={"size": LEGEND_SIZE, "weight": "bold"}
    )

    fig.subplots_adjust(
        left=0.07, right=0.97, top=0.92, bottom=0.09, hspace=0.37, wspace=0.18
    )
    heatmap_position = heat_ax.get_position()
    reduced_heatmap_height = heatmap_position.height * HEATMAP_HEIGHT_SCALE
    heat_ax.set_position(
        [
            heatmap_position.x0,
            heatmap_position.y0 + (heatmap_position.height - reduced_heatmap_height) / 2,
            heatmap_position.width,
            reduced_heatmap_height,
        ]
    )
    colorbar_position = colorbar.ax.get_position()
    colorbar.ax.set_position(
        [
            colorbar_position.x0,
            colorbar_position.y0 + (colorbar_position.height - reduced_heatmap_height) / 2,
            colorbar_position.width,
            reduced_heatmap_height,
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {output_path}")
    print(f"Saved: {output_path.with_suffix('.pdf')}")
    print(f"Heatmap source: {THEORY_RESULTS}")
    print(f"Heatmap observations: {int(heatmap.sum())}")

    print("\nSummary by case:")
    print(combined.to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args().output)
