#!/usr/bin/env python3
"""Plot how many recovered patterns are contained in each S graph.

For every result directory, this script inverts pattern_to_S_indices*.json:

    pattern -> [S indices]  becomes  S index -> number of patterns

It then plots the frequency distribution of those counts.  The x axis is the
number of patterns contained in an S graph and the logarithmic y axis is the
number of S graphs with that count.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


RUN_NAME_RE = re.compile(r"^input_color_(average|rare|uniform)_deg_(\d+)_")


@dataclass(frozen=True)
class Distribution:
    run_dir: Path
    source_file: Path
    color_mode: str
    degree: int
    is_partial: bool
    pattern_count: int
    s_count: int
    histogram: Counter[int]
    cumulative_covered_s: tuple[int, ...]
    ordered_pattern_names: tuple[str, ...]


def choose_index_file(run_dir: Path) -> tuple[Path, bool] | None:
    """Prefer a finished index, falling back to a recovery checkpoint."""
    final_path = run_dir / "pattern_to_S_indices.json"
    if final_path.is_file():
        return final_path, False
    partial_path = run_dir / "pattern_to_S_indices.partial.json"
    if partial_path.is_file():
        return partial_path, True
    return None


def load_distribution(run_dir: Path) -> Distribution:
    match = RUN_NAME_RE.match(run_dir.name)
    if not match:
        raise ValueError(f"Cannot extract color mode and degree from {run_dir.name}")

    selected = choose_index_file(run_dir)
    if selected is None:
        raise FileNotFoundError(f"No pattern_to_S_indices JSON in {run_dir}")
    index_path, is_partial = selected

    with (run_dir / "run_config.json").open() as handle:
        config = json.load(handle)
    with index_path.open() as handle:
        index_data = json.load(handle)

    s_count = int(config["S_count"])
    patterns = index_data["patterns"]
    patterns_per_s = [0] * s_count

    def pattern_number(item: tuple[str, object]) -> int:
        number_match = re.search(r"pattern_(\d+)", item[0])
        if not number_match:
            raise ValueError(f"Cannot extract pattern number from {item[0]!r}")
        return int(number_match.group(1))

    ordered_patterns = sorted(patterns.items(), key=pattern_number)
    covered_s: set[int] = set()
    cumulative_covered_s = []

    for pattern_name, pattern_data in ordered_patterns:
        # A repeated index within one pattern should not count as two patterns.
        indices = set(pattern_data["S_indices"])
        for s_index in indices:
            if not isinstance(s_index, int) or not 1 <= s_index <= s_count:
                raise ValueError(
                    f"Invalid S index {s_index!r} for {pattern_name} in {index_path}"
                )
            patterns_per_s[s_index - 1] += 1
        covered_s.update(indices)
        cumulative_covered_s.append(len(covered_s))

    histogram = Counter(patterns_per_s)
    if sum(histogram.values()) != s_count:
        raise AssertionError(f"Histogram for {run_dir.name} does not total {s_count}")

    return Distribution(
        run_dir=run_dir,
        source_file=index_path,
        color_mode=match.group(1),
        degree=int(match.group(2)),
        is_partial=is_partial,
        pattern_count=len(patterns),
        s_count=s_count,
        histogram=histogram,
        cumulative_covered_s=tuple(cumulative_covered_s),
        ordered_pattern_names=tuple(name for name, _ in ordered_patterns),
    )


def discover_distributions(results_dir: Path) -> list[Distribution]:
    distributions = []
    for run_dir in sorted(path for path in results_dir.iterdir() if path.is_dir()):
        if RUN_NAME_RE.match(run_dir.name) and choose_index_file(run_dir):
            distributions.append(load_distribution(run_dir))
    if not distributions:
        raise FileNotFoundError(f"No matching result directories found in {results_dir}")
    return distributions


def plot_distributions(distributions: list[Distribution], output_stem: Path) -> None:
    degrees = sorted({dist.degree for dist in distributions})
    if len(degrees) != 4:
        raise ValueError(f"Expected four degrees, found {degrees}")

    degree_colors = {
        3: "#0072B2",
        5: "#E69F00",
        8: "#009E73",
        15: "#CC79A7",
    }
    color_modes = ("average", "rare", "uniform")
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), sharex=True, sharey=True)
    max_x = max(max(dist.histogram) for dist in distributions)
    x_values = list(range(max_x + 1))
    bar_width = 0.2
    offsets = {
        degree: (position - (len(degrees) - 1) / 2) * bar_width
        for position, degree in enumerate(degrees)
    }

    for ax, color_mode in zip(axes, color_modes):
        mode_data = sorted(
            (dist for dist in distributions if dist.color_mode == color_mode),
            key=lambda item: item.degree,
        )
        for dist in mode_data:
            label = f"Degree {dist.degree}"
            if dist.is_partial:
                label += f" (partial: {dist.pattern_count} patterns)"
            ax.bar(
                [x + offsets[dist.degree] for x in x_values],
                [dist.histogram.get(x, 0) for x in x_values],
                width=bar_width,
                color=degree_colors[dist.degree],
                alpha=0.85,
                label=label,
                edgecolor="white",
                linewidth=0.25,
            )

        ax.set_title(f"{color_mode.capitalize()} color distribution", fontweight="bold")
        ax.set_yscale("log")
        ax.set_xlim(-0.6, max_x + 0.6)
        ax.set_ylim(0.8, 1200)
        ax.set_xticks(x_values)
        ax.grid(True, which="major", alpha=0.3)
        ax.grid(True, which="minor", axis="y", alpha=0.12)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, fontsize=9)

    fig.supxlabel("Number of recovered patterns contained in an S graph", fontsize=12)
    fig.supylabel("Number of S graphs (log scale)", fontsize=12)
    fig.suptitle(
        "Distribution of recovered-pattern membership across S graphs",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0.03, 0.03, 1, 0.95))
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_remaining_uncovered(
    distributions: list[Distribution], output_stem: Path
) -> None:
    """Plot S graphs not yet covered by any pattern in each prefix."""
    degrees = sorted({dist.degree for dist in distributions})
    color_modes = ("average", "rare", "uniform")
    mode_colors = {
        "average": "#2F7F98",
        "rare": "#D69A56",
        "uniform": "#78A5A3",
    }
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), sharex=True, sharey=True)

    for ax, degree in zip(axes.flat, degrees):
        degree_data = sorted(
            (dist for dist in distributions if dist.degree == degree),
            key=lambda item: color_modes.index(item.color_mode),
        )
        for dist in degree_data:
            x_values = range(0, dist.pattern_count + 1)
            remaining_s = [dist.s_count] + [
                dist.s_count - covered for covered in dist.cumulative_covered_s
            ]
            ax.plot(
                x_values,
                remaining_s,
                color=mode_colors[dist.color_mode],
                linewidth=2.8,
                label=dist.color_mode.capitalize(),
            )

        ax.set_title(f"Average degree {degree}", fontweight="bold")
        ax.set_yscale("log")
        ax.set_xlim(0, 200)
        ax.set_ylim(10, 1100)
        ax.set_xticks([0, 25, 50, 75, 100, 125, 150, 175, 200])
        ax.grid(True, which="major", alpha=0.3)
        ax.grid(True, which="minor", axis="y", alpha=0.12)
        ax.legend(frameon=False, fontsize=9)

    fig.supxlabel(
        "Number of patterns processed", fontsize=12, fontweight="bold"
    )
    fig.supylabel("S graphs still uncovered", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0.03, 0.03, 1, 0.99))
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_degree_3_vs_15(
    distributions: list[Distribution], output_stem: Path
) -> None:
    """Compare raw surviving-query curves for average degrees 3 and 15."""
    color_modes = ("average", "rare", "uniform")
    mode_colors = {
        "average": "#2F7F98",
        "rare": "#D69A56",
        "uniform": "#78A5A3",
    }
    degree_styles = {3: "-", 15: "--"}
    selected = {
        (dist.degree, dist.color_mode): dist
        for dist in distributions
        if dist.degree in degree_styles
    }
    expected = {(degree, mode) for degree in degree_styles for mode in color_modes}
    if set(selected) != expected:
        raise ValueError(
            "Expected Average/Rare/Uniform data for degrees 3 and 15; "
            f"found {sorted(selected)}"
        )

    fig, ax = plt.subplots(figsize=(5.2, 7.5))
    for degree in (3, 15):
        for color_mode in color_modes:
            dist = selected[(degree, color_mode)]
            x_values = range(0, dist.pattern_count + 1)
            remaining_s = [dist.s_count] + [
                dist.s_count - covered for covered in dist.cumulative_covered_s
            ]
            ax.plot(
                remaining_s,
                x_values,
                color=mode_colors[color_mode],
                linestyle=degree_styles[degree],
                linewidth=2.8,
            )

    ax.set_xscale("log")
    ax.set_xlim(10, 1000)
    ax.set_ylim(0, 200)
    ax.set_yticks([0, 25, 50, 75, 100, 125, 150, 175, 200])
    ax.set_xlabel(
        "S graphs still uncovered", fontsize=12, fontweight="bold", labelpad=8
    )
    ax.set_ylabel(
        "Number of patterns processed", fontsize=12, fontweight="bold", labelpad=8
    )
    ax.tick_params(axis="both", which="major", labelsize=10)
    for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        label.set_fontweight("bold")
    ax.grid(True, which="major", color="#D7DCE2", linewidth=0.8, alpha=0.75)
    ax.grid(True, which="minor", axis="x", color="#D7DCE2", linewidth=0.5, alpha=0.35)
    ax.set_axisbelow(True)

    distribution_handles = [
        Line2D([0], [0], color=mode_colors[mode], linewidth=2.8, label=mode.capitalize())
        for mode in color_modes
    ]
    degree_handles = [
        Line2D(
            [0],
            [0],
            color="#334155",
            linewidth=2.8,
            linestyle=degree_styles[degree],
            label=f"Average degree {degree}",
        )
        for degree in (3, 15)
    ]
    distribution_legend = ax.legend(
        handles=distribution_handles,
        title="Color distribution",
        loc="lower left",
        bbox_to_anchor=(0.02, 0.02),
        borderaxespad=0,
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1.0,
        fontsize=10,
        title_fontproperties={"weight": "bold", "size": 10},
    )
    ax.add_artist(distribution_legend)
    ax.legend(
        handles=degree_handles,
        title="Line style",
        loc="lower left",
        bbox_to_anchor=(0.02, 0.20),
        borderaxespad=0,
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1.0,
        fontsize=10,
        title_fontproperties={"weight": "bold", "size": 10},
    )

    fig.tight_layout()
    fig.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_distributions_by_degree(
    distributions: list[Distribution], output_stem: Path
) -> None:
    """Make four degree panels with three adjacent color-distribution bars."""
    degrees = sorted({dist.degree for dist in distributions})
    color_modes = ("average", "rare", "uniform")
    mode_colors = {
        "average": "#0072B2",
        "rare": "#D55E00",
        "uniform": "#009E73",
    }
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), sharex=True, sharey=True)
    max_x = max(max(dist.histogram) for dist in distributions)
    x_values = list(range(max_x + 1))
    bar_width = 0.26
    offsets = {
        mode: (position - (len(color_modes) - 1) / 2) * bar_width
        for position, mode in enumerate(color_modes)
    }

    for ax, degree in zip(axes.flat, degrees):
        degree_data = sorted(
            (dist for dist in distributions if dist.degree == degree),
            key=lambda item: color_modes.index(item.color_mode),
        )
        for dist in degree_data:
            label = dist.color_mode.capitalize()
            if dist.is_partial:
                label += f" (partial: {dist.pattern_count} patterns)"
            ax.bar(
                [x + offsets[dist.color_mode] for x in x_values],
                [dist.histogram.get(x, 0) for x in x_values],
                width=bar_width,
                color=mode_colors[dist.color_mode],
                alpha=0.85,
                label=label,
                edgecolor="white",
                linewidth=0.25,
            )

        ax.set_title(f"Average degree {degree}", fontweight="bold")
        ax.set_yscale("log")
        ax.set_xlim(-0.6, max_x + 0.6)
        ax.set_ylim(0.8, 1200)
        ax.set_xticks(x_values)
        ax.grid(True, which="major", alpha=0.3)
        ax.grid(True, which="minor", axis="y", alpha=0.12)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, fontsize=9)

    fig.supxlabel("Number of recovered patterns contained in an S graph", fontsize=12)
    fig.supylabel("Number of S graphs (log scale)", fontsize=12)
    fig.suptitle(
        "Recovered-pattern membership by average degree",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0.03, 0.03, 1, 0.95))
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_overlaid_degrees(
    distributions: list[Distribution], output_stem: Path
) -> None:
    """Overlay degree bars, using lower opacity for larger average degrees."""
    degrees = (3, 5, 8, 15)
    color_modes = ("average", "rare", "uniform")
    mode_colors = {
        "average": "#2F7F98",
        "rare": "#D69A56",
        "uniform": "#78A5A3",
    }
    mode_edge_colors = {
        "average": "#1F5F73",
        "rare": "#9C6530",
        "uniform": "#4F7876",
    }
    degree_alpha = {3: 0.95, 5: 0.72, 8: 0.48, 15: 0.25}
    selected = {
        (dist.degree, dist.color_mode): dist for dist in distributions
    }
    expected = {(degree, mode) for degree in degrees for mode in color_modes}
    if set(selected) != expected:
        raise ValueError(f"Missing overlaid histogram datasets: {sorted(expected - set(selected))}")

    max_x = max(max(dist.histogram) for dist in distributions)
    x_values = list(range(max_x + 1))
    bar_width = 0.26
    offsets = {
        mode: (position - 1) * bar_width
        for position, mode in enumerate(color_modes)
    }

    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    # Larger degrees are drawn later and more transparently, so every original
    # histogram remains visible while bars for the same distribution overlap.
    for degree in degrees:
        for mode in color_modes:
            dist = selected[(degree, mode)]
            ax.bar(
                [x + offsets[mode] for x in x_values],
                [dist.histogram.get(x, 0) for x in x_values],
                width=bar_width,
                facecolor=to_rgba(mode_colors[mode], 0.18),
                edgecolor=to_rgba(
                    mode_edge_colors[mode], degree_alpha[degree]
                ),
                linewidth=1.5,
                zorder=2 + degrees.index(degree),
            )

    ax.set_yscale("log")
    ax.set_xlim(-0.65, max_x + 0.65)
    ax.set_ylim(0.8, 1200)
    ax.set_xticks(x_values)
    ax.set_xlabel(
        "Number of recovered patterns contained in an S query",
        fontsize=11,
        fontweight="bold",
        labelpad=7,
    )
    ax.set_ylabel("Number of S queries", fontsize=11, fontweight="bold", labelpad=7)
    ax.tick_params(axis="both", labelsize=9)
    for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        label.set_fontweight("bold")
    ax.grid(True, which="major", color="#D7DCE2", linewidth=0.7, alpha=0.75)
    ax.grid(True, which="minor", axis="y", color="#D7DCE2", linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)

    color_handles = [
        Patch(
            facecolor=to_rgba(mode_colors[mode], 0.35),
            edgecolor=mode_edge_colors[mode],
            linewidth=1.5,
            label=mode.capitalize(),
        )
        for mode in color_modes
    ]
    degree_handles = [
        Patch(
            facecolor=to_rgba("#64748B", 0.18),
            edgecolor=to_rgba("#334155", degree_alpha[degree]),
            linewidth=1.5,
            label=rf"$d_S = {degree}$",
        )
        for degree in degrees
    ]
    degree_legend = ax.legend(
        handles=degree_handles,
        title=r"$d_S$ (opacity)",
        loc="upper right",
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1,
        prop={"size": 8, "weight": "bold"},
        title_fontproperties={"size": 8.5, "weight": "bold"},
    )
    ax.add_artist(degree_legend)
    ax.legend(
        handles=color_handles,
        title="Color distribution",
        loc="upper right",
        bbox_to_anchor=(1.0, 0.76),
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1,
        prop={"size": 8, "weight": "bold"},
        title_fontproperties={"size": 8.5, "weight": "bold"},
    )

    fig.tight_layout()
    fig.savefig(output_stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[2]
    default_results = repository_root / "data" / "results" / "vista_plus"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=default_results)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repository_root / "figures" / "output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    distributions = discover_distributions(results_dir)
    expected = {(mode, degree) for mode in ("average", "rare", "uniform") for degree in (3, 5, 8, 15)}
    actual = {(dist.color_mode, dist.degree) for dist in distributions}
    if actual != expected or len(distributions) != len(expected):
        raise ValueError(
            "Expected exactly one run for each of the 12 color/degree combinations; "
            f"found {len(distributions)} runs with combinations {sorted(actual)}"
        )

    stem = output_dir / "patterns_per_S_log_frequency"
    plot_distributions(distributions, stem)
    plot_distributions_by_degree(
        distributions, output_dir / "patterns_per_S_log_frequency_by_degree"
    )
    plot_overlaid_degrees(
        distributions, output_dir / "patterns_per_S_log_frequency_overlaid_degrees"
    )
    remaining_stem = output_dir / "remaining_uncovered_S_by_patterns"
    plot_remaining_uncovered(distributions, remaining_stem)
    plot_degree_3_vs_15(
        distributions, output_dir / "surviving_queries_degree_3_vs_15"
    )

    partial = [dist for dist in distributions if dist.is_partial]
    print(f"Processed {len(distributions)} datasets; wrote outputs under {output_dir}")
    for dist in partial:
        print(f"NOTE: used partial file for {dist.run_dir.name} ({dist.pattern_count} patterns)")


if __name__ == "__main__":
    main()
