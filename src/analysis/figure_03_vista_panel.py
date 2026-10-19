#!/usr/bin/env python3
"""Plot VISTA query-survival matrices from the saved summary CSV files."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, SymLogNorm


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
DEFAULT_INPUT = REPOSITORY_ROOT / "data" / "results" / "vista" / "synthetic_summaries"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "figures" / "figure_03" / "vista_panel.png"

FAMILIES = ("average", "rare", "uniform")
DEGREES = (3, 5, 8, 15)
CONFIGURATIONS = tuple((family, degree) for family in FAMILIES for degree in DEGREES)
SHORT_NAMES = {"average": "A", "rare": "R", "uniform": "U"}
FILE_RE = re.compile(
    r"^query_(average|rare|uniform)_deg_(3|5|8|15)"
    r"__G_(average|rare|uniform)_deg_(3|5|8|15)\.csv$"
)
S_RE = re.compile(r"^S_(\d+)$")

# Cohesive muted cream-gold-sage-teal palette for publication figures.
LAPAZ = LinearSegmentedColormap.from_list(
    "muted_survival",
    (
        "#FAF8F2",
        "#EADFCB",
        "#E4C58F",
        "#D69A56",
        "#A9A66F",
        "#78A5A3",
        "#4B8FA8",
    ),
)


def read_summaries(input_dir: Path) -> dict[tuple[str, int, str, int], dict[int, int | None]]:
    results: dict[tuple[str, int, str, int], dict[int, int | None]] = {}
    for path in sorted(input_dir.glob("query_*__G_*.csv")):
        match = FILE_RE.fullmatch(path.name)
        if match is None:
            continue
        key = (match.group(1), int(match.group(2)), match.group(3), int(match.group(4)))
        values: dict[int, int | None] = {}
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                s_match = S_RE.fullmatch(row.get("S_NAME", "").strip())
                if s_match is None:
                    raise ValueError(f"Invalid S_NAME in {path}: {row}")
                s_id = int(s_match.group(1))
                if s_id in values:
                    raise ValueError(f"Duplicate S_{s_id} in {path}")
                raw_size = row.get("first_not_found_size", "").strip()
                values[s_id] = int(raw_size) if raw_size else None
        if key in results:
            raise ValueError(f"Duplicate configuration: {key}")
        results[key] = values

    expected = {
        (s_family, s_degree, g_family, g_degree)
        for s_family, s_degree in CONFIGURATIONS
        for g_family, g_degree in CONFIGURATIONS
    }
    missing = sorted(expected - results.keys())
    extra = sorted(results.keys() - expected)
    if missing or extra:
        raise ValueError(
            f"Expected 144 configurations; missing={missing}, extra={extra}"
        )
    counts = {len(values) for values in results.values()}
    if counts != {1000}:
        raise ValueError(f"Expected 1000 S rows per configuration; found {sorted(counts)}")
    return results


def build_matrices(
    results: dict[tuple[str, int, str, int], dict[int, int | None]], max_k: int
) -> dict[int, np.ndarray]:
    matrices = {k: np.zeros((12, 12), dtype=int) for k in range(1, max_k + 1)}
    for row, (s_family, s_degree) in enumerate(CONFIGURATIONS):
        for column, (g_family, g_degree) in enumerate(CONFIGURATIONS):
            values = results[(s_family, s_degree, g_family, g_degree)].values()
            for k, matrix in matrices.items():
                matrix[row, column] = sum(size is None or size > k for size in values)
    return matrices


def draw(input_dir: Path, output: Path, max_k: int) -> None:
    results = read_summaries(input_dir)
    matrices = build_matrices(results, max_k)
    x_labels = [f"{SHORT_NAMES[family]}\n{degree}" for family, degree in CONFIGURATIONS]
    y_labels = [f"{SHORT_NAMES[family]} {degree}" for family, degree in CONFIGURATIONS]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.titleweight": "bold",
        }
    )
    n_columns = 5
    fig, axes = plt.subplots(2, n_columns, figsize=(29, 12.5), constrained_layout=False)
    fig.patch.set_facecolor("white")
    image = None
    for index, (k, matrix) in enumerate(matrices.items()):
        ax = axes.flat[index]
        image = ax.imshow(
            matrix,
            cmap=LAPAZ,
            norm=SymLogNorm(linthresh=1, vmin=0, vmax=1000, base=10),
            aspect="auto",
        )
        ax.set_title(f"k = {k}", fontsize=19, fontweight="bold", pad=15)
        ax.set_xticks(range(12), labels=x_labels)
        ax.set_yticks(range(12), labels=y_labels)
        ax.tick_params(axis="x", labelsize=12, length=0, pad=8)
        ax.tick_params(axis="y", labelsize=14, length=0, pad=7)
        for label in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
            label.set_fontweight("bold")
        if index % n_columns != 0:
            ax.tick_params(labelleft=False)
        ax.set_xticks(np.arange(-0.5, 12, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 12, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.05, alpha=0.9)
        ax.tick_params(which="minor", bottom=False, left=False)
        for boundary in (3.5, 7.5):
            ax.axvline(boundary, color="#ffffff", linewidth=2.4)
            ax.axhline(boundary, color="#ffffff", linewidth=2.4)
        for spine in ax.spines.values():
            spine.set_color("#475569")
            spine.set_linewidth(0.8)

    for ax in axes.flat[len(matrices) :]:
        ax.set_visible(False)

    fig.supxlabel("Background graph configuration, G", fontsize=25, fontweight="bold", y=0.035)
    fig.supylabel("Query configuration, S", fontsize=25, fontweight="bold", x=0.018)
    fig.text(
        0.925,
        0.965,
        "A = Average\nR = Rare\nU = Uniform",
        ha="left",
        va="top",
        fontsize=13,
        fontweight="bold",
        linespacing=1.25,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#F7FAFC", "edgecolor": "#8292A3"},
    )
    fig.subplots_adjust(left=0.075, right=0.91, top=0.95, bottom=0.105, wspace=0.08, hspace=0.30)
    colorbar_ax = fig.add_axes((0.928, 0.16, 0.018, 0.64))
    colorbar = fig.colorbar(image, cax=colorbar_ax, ticks=(0, 1, 10, 100, 1000))
    colorbar.set_label("S queries still alive", fontsize=25, fontweight="bold", labelpad=13)
    colorbar.ax.tick_params(labelsize=12)
    for label in colorbar.ax.get_yticklabels():
        label.set_fontweight("bold")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {output} and {output.with_suffix('.pdf')} from 144 summaries")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-k", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.max_k <= 10:
        parser.error("--max-k must be between 1 and 10")
    draw(args.input_dir, args.output, args.max_k)


if __name__ == "__main__":
    main()
