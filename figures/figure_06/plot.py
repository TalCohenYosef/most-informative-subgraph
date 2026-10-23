#!/usr/bin/env python3
"""Create one data-driven figure containing the recovery analysis panels."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, SymLogNorm, to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "figures" / "analysis"))

from figure_06_matrix import COMBINATIONS, build_matrix, find_run_directories
from figure_06_membership import Distribution, discover_distributions


MODE_ORDER = ("average", "rare", "uniform")
MODE_COLORS = {
    "average": "#2F7F98",
    "rare": "#D69A56",
    "uniform": "#78A5A3",
}

AXIS_LABEL_SIZE = 12
TICK_LABEL_SIZE = 10
PANEL_TITLE_SIZE = 8
LEGEND_TEXT_SIZE = 8
LEGEND_TITLE_SIZE = 8.5


def make_text_bold(ax: plt.Axes) -> None:
    for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        label.set_fontweight("bold")


def draw_heatmap(
    fig: plt.Figure,
    ax: plt.Axes,
    matrix: np.ndarray,
    partial_rows: set[tuple[str, int]],
) -> None:
    cmap = LinearSegmentedColormap.from_list(
        "light_recovery_palette",
        ["#FDF9F1", "#FAF1DF", "#F1D6A5", "#E6B96F", "#AFC4B4", "#8EC1CF"],
    )
    cmap.set_bad("#FFFFFF")
    image = ax.imshow(
        np.ma.masked_invalid(matrix),
        cmap=cmap,
        norm=SymLogNorm(linthresh=1, linscale=1, vmin=0, vmax=1000, base=10),
        aspect="equal",
    )
    # Keep the square heatmap aligned with the left histogram column instead
    # of letting Matplotlib center it within its wider GridSpec cell.
    ax.set_anchor("W")

    abbreviations = {"average": "A", "rare": "R", "uniform": "U"}
    x_labels = [f"{abbreviations[mode]}\n{degree}" for mode, degree in COMBINATIONS]
    y_labels = [
        f"{abbreviations[mode]} {degree}{'*' if (mode, degree) in partial_rows else ''}"
        for mode, degree in COMBINATIONS
    ]
    ax.set_xticks(range(12), labels=x_labels)
    ax.set_yticks(range(12), labels=y_labels)
    ax.set_xlabel(
        "Reference graph configuration, G",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=6,
    )
    ax.set_ylabel(
        "Query configuration, S",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=7,
    )
    ax.tick_params(
        axis="both", which="major", length=0, labelsize=TICK_LABEL_SIZE, pad=3
    )
    ax.xaxis.tick_bottom()
    ax.xaxis.set_label_position("bottom")
    make_text_bold(ax)

    ax.set_xticks(np.arange(-0.5, 12, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 12, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.1)
    ax.tick_params(which="minor", bottom=False, left=False)
    for boundary in (3.5, 7.5):
        ax.axvline(boundary, color="white", linewidth=2.7)
        ax.axhline(boundary, color="white", linewidth=2.7)
    for row_start in (-0.5, 3.5, 7.5):
        for column_start in (-0.5, 3.5, 7.5):
            ax.add_patch(
                Rectangle(
                    (column_start, row_start),
                    4,
                    4,
                    fill=False,
                    edgecolor="black",
                    linewidth=0.55,
                    zorder=4,
                )
            )
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(0.8)
    if partial_rows:
        partial_labels = ", ".join(
            f"{abbreviations[mode]}{degree}" for mode, degree in sorted(partial_rows)
        )
        ax.text(
            0.0,
            1.015,
            f"* {partial_labels}: partial G-search checkpoints",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=LEGEND_TEXT_SIZE,
            fontweight="bold",
        )

    colorbar_ax = inset_axes(
        ax,
        width="3.8%",
        height="78%",
        loc="center left",
        bbox_to_anchor=(1.075, -0.035, 1.0, 1.0),
        bbox_transform=ax.transAxes,
        borderpad=0,
    )
    colorbar = fig.colorbar(image, cax=colorbar_ax)
    colorbar.set_label(
        "S queries still alive",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=8,
    )
    colorbar.set_ticks([0, 1, 10, 100, 1000])
    colorbar.set_ticklabels(["0", r"$10^0$", r"$10^1$", r"$10^2$", r"$10^3$"])
    colorbar.ax.yaxis.set_ticks_position("right")
    colorbar.ax.yaxis.set_label_position("right")
    colorbar.ax.tick_params(labelsize=TICK_LABEL_SIZE)
    colorbar.ax.yaxis.label.set_fontweight("bold")
    for label in colorbar.ax.get_yticklabels():
        label.set_fontweight("bold")
    colorbar.ax.text(
        1.5,
        1.08,
        "A = Average\nR = Rare\nU = Uniform",
        transform=colorbar.ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=LEGEND_TEXT_SIZE,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "#F7FAFC",
            "edgecolor": "#8AA0B5",
            "linewidth": 0.6,
        },
    )


def select_trend_data(distributions: list[Distribution]) -> dict[tuple[int, str], Distribution]:
    selected = {
        (dist.degree, dist.color_mode): dist
        for dist in distributions
        if dist.degree in (3, 15)
    }
    expected = {(degree, mode) for degree in (3, 15) for mode in MODE_ORDER}
    if set(selected) != expected:
        raise ValueError(f"Missing trend datasets: {sorted(expected - set(selected))}")
    return selected


def draw_trends(ax: plt.Axes, distributions: list[Distribution]) -> None:
    selected = select_trend_data(distributions)
    degree_styles = {3: "-", 15: "--"}
    for degree in (3, 15):
        for mode in MODE_ORDER:
            dist = selected[(degree, mode)]
            remaining = [dist.s_count] + [
                dist.s_count - covered for covered in dist.cumulative_covered_s
            ]
            ax.plot(
                range(dist.pattern_count + 1),
                remaining,
                color=MODE_COLORS[mode],
                linestyle=degree_styles[degree],
                linewidth=1.8,
            )

    ax.set_xlim(0, 175)
    ax.set_xticks(range(0, 176, 25))
    ax.set_yscale("log")
    ax.set_ylim(10, 1000)
    ax.set_xlabel(
        "Number of patterns processed",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=5,
    )
    ax.set_ylabel(
        "S queries still uncovered",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=5,
    )
    ax.tick_params(axis="both", labelsize=TICK_LABEL_SIZE)
    ax.xaxis.tick_bottom()
    ax.xaxis.set_label_position("bottom")
    make_text_bold(ax)
    ax.grid(True, which="major", color="#D7DCE2", linewidth=0.65, alpha=0.75)
    ax.grid(True, which="minor", axis="y", color="#D7DCE2", linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)

    distribution_handles = [
        Line2D([0], [0], color=MODE_COLORS[mode], linewidth=1.8, label=mode.capitalize())
        for mode in MODE_ORDER
    ]
    degree_handles = [
        Line2D(
            [0],
            [0],
            color="#334155",
            linewidth=1.8,
            linestyle=degree_styles[degree],
            label=f"Average degree {degree}",
        )
        for degree in (3, 15)
    ]
    style_legend = ax.legend(
        handles=degree_handles,
        title="Line style",
        loc="upper right",
        bbox_to_anchor=(0.98, 0.98),
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1,
        prop={"size": LEGEND_TEXT_SIZE, "weight": "bold"},
        title_fontproperties={"weight": "bold", "size": LEGEND_TITLE_SIZE},
    )
    ax.add_artist(style_legend)
    ax.legend(
        handles=distribution_handles,
        title="Color distribution",
        loc="upper right",
        bbox_to_anchor=(0.98, 0.76),
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1,
        prop={"size": LEGEND_TEXT_SIZE, "weight": "bold"},
        title_fontproperties={"weight": "bold", "size": LEGEND_TITLE_SIZE},
    )


def draw_overlaid_histograms(
    ax: plt.Axes, distributions: list[Distribution]
) -> None:
    """Overlay all degrees; fill opacity is fixed and outline opacity encodes degree."""
    degrees = (3, 5, 8, 15)
    degree_alpha = {3: 0.95, 5: 0.72, 8: 0.48, 15: 0.25}
    edge_colors = {
        "average": "#1F5F73",
        "rare": "#9C6530",
        "uniform": "#4F7876",
    }
    selected = {(dist.degree, dist.color_mode): dist for dist in distributions}
    expected = {(degree, mode) for degree in degrees for mode in MODE_ORDER}
    if set(selected) != expected:
        raise ValueError(f"Missing histogram datasets: {sorted(expected - set(selected))}")

    maximum = max(max(dist.histogram) for dist in distributions)
    x_values = list(range(maximum + 1))
    width = 0.25
    offsets = {mode: (position - 1) * width for position, mode in enumerate(MODE_ORDER)}
    for degree in degrees:
        for mode in MODE_ORDER:
            dist = selected[(degree, mode)]
            ax.bar(
                [x + offsets[mode] for x in x_values],
                [dist.histogram.get(x, 0) for x in x_values],
                width=width,
                facecolor=to_rgba(MODE_COLORS[mode], 0.18),
                edgecolor=to_rgba(edge_colors[mode], degree_alpha[degree]),
                linewidth=1.0,
                zorder=2 + degrees.index(degree),
            )

    ax.set_yscale("log")
    ax.set_xlim(-0.6, maximum + 0.6)
    ax.set_ylim(0.8, 1200)
    tick_step = 1 if maximum <= 20 else 2
    ax.set_xticks(range(0, maximum + 1, tick_step))
    ax.set_xlabel(
        "Number of recovered patterns contained in an S query",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=5,
    )
    ax.set_ylabel(
        "Number of S queries",
        fontsize=AXIS_LABEL_SIZE,
        fontweight="bold",
        labelpad=5,
    )
    ax.tick_params(axis="both", labelsize=TICK_LABEL_SIZE)
    make_text_bold(ax)
    ax.grid(True, which="major", color="#D7DCE2", linewidth=0.55, alpha=0.7)
    ax.grid(True, which="minor", axis="y", color="#D7DCE2", linewidth=0.3, alpha=0.3)
    ax.set_axisbelow(True)

    color_handles = [
        Patch(
            facecolor=to_rgba(MODE_COLORS[mode], 0.35),
            edgecolor=edge_colors[mode],
            linewidth=1.0,
            label=mode.capitalize(),
        )
        for mode in MODE_ORDER
    ]
    degree_handles = [
        Patch(
            facecolor=to_rgba("#64748B", 0.18),
            edgecolor=to_rgba("#334155", degree_alpha[degree]),
            linewidth=1.0,
            label=rf"$d_S = {degree}$",
        )
        for degree in degrees
    ]
    degree_legend = ax.legend(
        handles=degree_handles,
        title=r"$d_S$ (outline opacity)",
        loc="upper right",
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1,
        prop={"size": LEGEND_TEXT_SIZE, "weight": "bold"},
        title_fontproperties={"size": LEGEND_TITLE_SIZE, "weight": "bold"},
    )
    for label in degree_legend.get_texts():
        label.set_fontweight("bold")
    ax.add_artist(degree_legend)
    ax.legend(
        handles=color_handles,
        title="Color distribution",
        loc="upper right",
        bbox_to_anchor=(0.98, 0.5),
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1,
        prop={"size": LEGEND_TEXT_SIZE, "weight": "bold"},
        title_fontproperties={"size": LEGEND_TITLE_SIZE, "weight": "bold"},
    )


def create_figure(
    matrix: np.ndarray,
    distributions: list[Distribution],
    output_path: Path,
    partial_heatmap_rows: set[tuple[str, int]],
) -> None:
    fig = plt.figure(figsize=(10, 7.1))
    # The histogram occupies the top row; trend and heatmap panels sit below.
    grid = fig.add_gridspec(
        2,
        1,
        height_ratios=(0.78, 1.12),
        hspace=0.24,
    )

    histogram_ax = fig.add_subplot(grid[0, :])
    bottom_grid = grid[1, 0].subgridspec(
        1, 2, width_ratios=(1.2, 1.0), wspace=0.24
    )
    trend_ax = fig.add_subplot(bottom_grid[0, 0])
    heatmap_ax = fig.add_subplot(bottom_grid[0, 1])
    draw_heatmap(fig, heatmap_ax, matrix, partial_heatmap_rows)
    draw_trends(trend_ax, distributions)

    draw_overlaid_histograms(histogram_ax, distributions)

    fig.subplots_adjust(left=0.07, right=0.97, top=0.975, bottom=0.085)
    histogram_position = histogram_ax.get_position()
    histogram_ax.set_position(
        [
            histogram_position.x0 + 0.01,
            histogram_position.y0 + 0.01,
            histogram_position.width + 0.04,
            histogram_position.height + 0.03,
        ]
    )
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote figure PDF to {output_path.with_suffix('.pdf')}")


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[2]
    default_results = repository_root / "data" / "results" / "vista_plus"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=default_results)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "figure_06.png",
    )
    parser.add_argument(
        "--skip-heatmap-row",
        action="append",
        default=[],
        metavar="MODE:DEGREE",
        help="Leave one unfinished S-run row blank in the heatmap (repeatable)",
    )
    parser.add_argument(
        "--partial-heatmap-row",
        action="append",
        default=[],
        metavar="MODE:DEGREE",
        help="Use in-progress G-search checkpoints for an unfinished S-run row",
    )
    return parser.parse_args()


def parse_heatmap_rows(values: list[str]) -> set[tuple[str, int]]:
    rows = set()
    for value in values:
        try:
            mode, degree_text = value.split(":", 1)
            key = (mode, int(degree_text))
        except ValueError as exc:
            raise ValueError(
                f"Invalid --skip-heatmap-row {value!r}; expected MODE:DEGREE"
            ) from exc
        if key not in COMBINATIONS:
            raise ValueError(f"Unknown heatmap row: {value!r}")
        rows.add(key)
    return rows


def main() -> None:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    skipped_heatmap_rows = parse_heatmap_rows(args.skip_heatmap_row)
    requested_partial_rows = parse_heatmap_rows(args.partial_heatmap_row)
    if skipped_heatmap_rows & requested_partial_rows:
        raise ValueError("A heatmap row cannot be both skipped and partial")
    run_dirs = find_run_directories(
        results_dir,
        allow_missing=skipped_heatmap_rows,
        allow_partial=requested_partial_rows,
    )
    for key in skipped_heatmap_rows:
        run_dirs.pop(key, None)
    matrix = build_matrix(run_dirs)
    distributions = discover_distributions(results_dir)
    actual_partial_rows = {
        key for key in requested_partial_rows
        if key in run_dirs and not (run_dirs[key] / "G_summary.txt").is_file()
    }
    create_figure(
        matrix,
        distributions,
        output_path,
        actual_partial_rows,
    )
    print(f"Wrote data-driven composite figure to {output_path}")


if __name__ == "__main__":
    main()
