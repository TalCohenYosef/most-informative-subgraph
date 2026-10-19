#!/usr/bin/env python3
"""Build an S-input by background-G elimination-rate heatmap."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
from matplotlib.patches import Rectangle


MODES = ("average", "rare", "uniform")
DEGREES = (3, 5, 8, 15)
COMBINATIONS = tuple((mode, degree) for mode in MODES for degree in DEGREES)
RUN_RE = re.compile(r"^input_color_(average|rare|uniform)_deg_(\d+)_")
SUMMARY_RE = re.compile(
    r"^G_(average|rare|uniform)_deg_(\d+):\s+"
    r"(\d+)/(\d+) S eliminated \((\d+) undetermined\)"
)


def find_run_directories(
    results_dir: Path,
    *,
    allow_missing: set[tuple[str, int]] | None = None,
    allow_partial: set[tuple[str, int]] | None = None,
) -> dict[tuple[str, int], Path]:
    allow_missing = allow_missing or set()
    allow_partial = allow_partial or set()
    unknown_allowed = (allow_missing | allow_partial) - set(COMBINATIONS)
    if unknown_allowed:
        raise ValueError(f"Unknown allowed-missing combinations: {unknown_allowed}")
    run_dirs: dict[tuple[str, int], Path] = {}
    for path in sorted(results_dir.iterdir()):
        match = RUN_RE.match(path.name)
        if not path.is_dir() or not match:
            continue
        key = (match.group(1), int(match.group(2)))
        has_final = (path / "G_summary.txt").is_file()
        has_partial = (
            key in allow_partial
            and (path / "pattern_to_S_indices.json").is_file()
            and (path / "G_search_checkpoints").is_dir()
        )
        if not has_final and not has_partial:
            continue
        if key in run_dirs:
            raise ValueError(f"Multiple G_summary.txt files found for {key}")
        run_dirs[key] = path

    missing = set(COMBINATIONS) - set(run_dirs)
    extra = set(run_dirs) - set(COMBINATIONS)
    unexpected_missing = missing - allow_missing
    if unexpected_missing or extra:
        raise ValueError(
            f"Unexpected input combinations; missing={unexpected_missing}, extra={extra}"
        )
    return run_dirs


def read_summary(path: Path) -> dict[tuple[str, int], tuple[int, int, int]]:
    values: dict[tuple[str, int], tuple[int, int, int]] = {}
    for line in path.read_text().splitlines():
        match = SUMMARY_RE.match(line)
        if not match:
            continue
        key = (match.group(1), int(match.group(2)))
        values[key] = (int(match.group(3)), int(match.group(4)), int(match.group(5)))
    if set(values) != set(COMBINATIONS):
        raise ValueError(f"Expected 12 G rows in {path}; found {len(values)}")
    return values


def read_partial_summary(run_dir: Path) -> dict[tuple[str, int], tuple[int, int, int]]:
    """Build comparable current results from the common completed G-check prefix."""
    config = json.loads((run_dir / "run_config.json").read_text())
    index_data = json.loads((run_dir / "pattern_to_S_indices.json").read_text())
    patterns = index_data["patterns"]
    checkpoint_root = run_dir / "G_search_checkpoints"
    checkpoints = {}
    for mode, degree in COMBINATIONS:
        g_name = f"G_{mode}_deg_{degree}"
        checkpoint_path = checkpoint_root / f"{g_name}.json"
        if not checkpoint_path.is_file():
            raise ValueError(f"Missing partial G checkpoint: {checkpoint_path}")
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoints[(mode, degree)] = checkpoint["pattern_checks"]

    common_patterns = set.intersection(
        *(set(checks) for checks in checkpoints.values())
    )
    eligible_common = {
        name for name in common_patterns
        if patterns[name]["meets_alive_threshold"]
    }
    total = int(config["S_count"])
    values = {}
    for g_key, checks in checkpoints.items():
        eliminated_indices = set()
        incomplete = 0
        for pattern_name in eligible_common:
            status = checks[pattern_name]["status"]
            if status == "absent":
                eliminated_indices.update(patterns[pattern_name]["S_indices"])
            elif status in {"timeout", "error"}:
                incomplete += 1
        values[g_key] = (len(eliminated_indices), total, incomplete)
    print(
        f"Using {len(eligible_common)} commonly completed pattern checks for "
        f"partial heatmap row {run_dir.name}"
    )
    return values


def build_matrix(
    run_dirs: dict[tuple[str, int], Path],
) -> np.ndarray:
    matrix = np.full((len(COMBINATIONS), len(COMBINATIONS)), np.nan, dtype=float)
    for row, s_key in enumerate(COMBINATIONS):
        if s_key not in run_dirs:
            continue
        run_dir = run_dirs[s_key]
        summary_path = run_dir / "G_summary.txt"
        summary = (
            read_summary(summary_path)
            if summary_path.is_file()
            else read_partial_summary(run_dir)
        )
        for column, g_key in enumerate(COMBINATIONS):
            eliminated, total, _undetermined = summary[g_key]
            matrix[row, column] = total - eliminated
    return matrix


def plot_matrix(
    matrix: np.ndarray, output_stem: Path, *, log_scale: bool = False
) -> None:
    # Low values are pale; increasing alive counts progress through orange to teal/blue.
    colors = (
        ["#FDF9F1", "#FAF1DF", "#F1D6A5", "#E6B96F", "#AFC4B4", "#8EC1CF"]
        if log_scale
        else ["#FFFFFF", "#F3E4C5", "#E1B56F", "#D69A56", "#78A5A3", "#69AABD"]
    )
    cmap = LinearSegmentedColormap.from_list(
        "white_orange_teal_blue",
        colors,
    )
    fig, ax = plt.subplots(figsize=(13.5, 11))
    norm = (
        LogNorm(vmin=50, vmax=1000)
        if log_scale
        else Normalize(vmin=0, vmax=1000)
    )
    image = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="equal")

    abbreviations = {"average": "A", "uniform": "U", "rare": "R"}
    labels = [f"{abbreviations[mode]}\n{degree}" for mode, degree in COMBINATIONS]
    ax.set_xticks(range(len(COMBINATIONS)), labels=labels)
    ax.set_yticks(range(len(COMBINATIONS)), labels=labels)
    ax.xaxis.tick_bottom()
    ax.xaxis.set_label_position("bottom")
    ax.set_xlabel(
        "Reference graph configuration, G", fontsize=13, fontweight="bold", labelpad=14
    )
    ax.set_ylabel("Query configuration, S", fontsize=13, fontweight="bold", labelpad=14)
    ax.tick_params(axis="x", length=0, pad=7, labeltop=False, labelbottom=True)
    ax.tick_params(axis="y", length=0, pad=7)
    for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        label.set_fontweight("bold")

    # Thin white cell boundaries and stronger separators between color families.
    ax.set_xticks(np.arange(-0.5, len(COMBINATIONS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(COMBINATIONS), 1), minor=True)
    gap_color = "white"
    ax.grid(which="minor", color=gap_color, linewidth=1.8 if log_scale else 0.8)
    ax.tick_params(which="minor", bottom=False, left=False)
    for boundary in (3.5, 7.5):
        ax.axvline(boundary, color=gap_color, linewidth=4 if log_scale else 3)
        ax.axhline(boundary, color=gap_color, linewidth=4 if log_scale else 3)
    if log_scale:
        # Outline only the nine 4x4 distribution blocks, not individual cells.
        for row_start in (-0.5, 3.5, 7.5):
            for column_start in (-0.5, 3.5, 7.5):
                ax.add_patch(
                    Rectangle(
                        (column_start, row_start),
                        4,
                        4,
                        fill=False,
                        edgecolor="black",
                        linewidth=0.75,
                        zorder=4,
                    )
                )
    for spine in ax.spines.values():
        spine.set_visible(log_scale)
        if log_scale:
            spine.set_color("black")
            spine.set_linewidth(1.1)
            spine.set_zorder(6)

    colorbar = fig.colorbar(
        image, ax=ax, fraction=0.045, pad=0.035, shrink=0.78, anchor=(0.0, 0.42)
    )
    colorbar.set_label(
        "S queries still alive",
        fontsize=12,
        fontweight="bold",
        labelpad=12,
    )
    if log_scale:
        colorbar.set_ticks([50, 100, 1000])
        colorbar.set_ticklabels(["50", r"$10^2$", r"$10^3$"])
    else:
        colorbar.set_ticks([0, 250, 500, 750, 1000])
    for label in colorbar.ax.get_yticklabels():
        label.set_fontweight(
            "normal" if log_scale and label.get_text() == "50" else "bold"
        )
    colorbar.ax.text(
        0.5,
        1.08,
        "A = Average\nR = Rare\nU = Uniform",
        transform=colorbar.ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "#F7FAFC",
            "edgecolor": "#8AA0B5",
            "linewidth": 0.8,
        },
    )
    fig.tight_layout()
    fig.savefig(output_stem.with_suffix(".png"), dpi=220, bbox_inches="tight")
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

    run_dirs = find_run_directories(results_dir)
    matrix = build_matrix(run_dirs)
    output_stem = output_dir / "G_by_S_still_alive_matrix"
    plot_matrix(matrix, output_stem)
    plot_matrix(
        matrix,
        output_dir / "G_by_S_still_alive_matrix_log_light",
        log_scale=True,
    )
    print(f"Read 12 G_summary.txt files and wrote the 12x12 matrix under {output_dir}")


if __name__ == "__main__":
    main()
