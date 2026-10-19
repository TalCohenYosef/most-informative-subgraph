#!/usr/bin/env python3
"""Shared result readers for VISTA and Subgraph_Counts plots."""

from __future__ import annotations

import csv
import io
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPHLETS = ROOT / "data" / "results" / "graphlets"
DEFAULT_PATTERN_FINDER = ROOT / "data" / "results" / "vista" / "case_summaries"
DEFAULT_RECOVERED_COUNTS = ROOT / "data" / "results" / "recovered_comparison_counts.csv"


def resolve_graphlets_root(root: Path) -> Path:
    """Accept either the timing root or its parent folder."""
    candidates = [root, root / "timing_1000_queries"]
    for candidate in candidates:
        if (candidate / "filter_results").exists():
            return candidate
    return root

S_GRAPHLET_RE = re.compile(
    r"^(?:query_)?(avg|average|rare|uniform)_deg_?(3|5|8|15)$"
)
G_GRAPHLET_RE = re.compile(
    r"^G_(average|rare|uniform)_deg_(3|5|8|15)_graphlet_cache_filtering_result_.*\.csv$"
)
S_PATTERN_RE = re.compile(
    r"^results_queris_(average|rare|uniform)_deg_(3|5|8|15)$"
)
G_PATTERN_RE = re.compile(
    r"^recovery_result_(?:G_)?(average|rare|uniform)_deg_(3|5|8|15)(?:_avg_s5)?$"
)
S_FILE_RE = re.compile(r"^S_(\d+)(?:\.json)?$")
Key = tuple[str, int, str, int]
CountSeries = tuple[int, tuple[int, ...]]


def _csv_source(path: Path):
    """Open a CSV, falling back to its tracked pre-deletion Git blob."""
    if path.stat().st_size:
        return path.open(newline="")
    relative = path.relative_to(ROOT)
    tracked_path = Path("local_tests") / relative
    listing = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            "HEAD",
            tracked_path.parent.as_posix(),
        ],
        cwd=ROOT.parent,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    prefix = path.name.split("_result_")[0] + "_result_"
    candidates = [item for item in listing if Path(item).name.startswith(prefix)]
    if candidates:
        tracked_path = Path(max(candidates))
    else:
        raise FileNotFoundError(f"No nonempty or tracked result for {path}")
    result = subprocess.run(
        ["git", "show", f"HEAD:{tracked_path.as_posix()}"],
        cwd=ROOT.parent,
        text=True,
        capture_output=True,
        check=True,
    )
    return io.StringIO(result.stdout)


def read_graphlets(root: Path) -> dict[Key, tuple[dict[int, int], Path]]:
    """Load the newest Subgraph_Counts result for each S/G configuration."""
    root = resolve_graphlets_root(root)
    newest: dict[Key, Path] = {}
    patterns = (
        "filter_results/**/G_*_graphlet_cache_filtering_result_*.csv",
        "filter_results/G_*_graphlet_cache_filtering_result_*.csv",
    )
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.parent.name.startswith("G_"):
                query_name = path.parent.parent.name
            else:
                query_name = path.parent.parent.name
            s_match = S_GRAPHLET_RE.fullmatch(query_name)
            g_match = G_GRAPHLET_RE.fullmatch(path.name)
            if s_match is None or g_match is None:
                continue
            family = "average" if s_match.group(1) == "avg" else s_match.group(1)
            key = (
                family,
                int(s_match.group(2)),
                g_match.group(1),
                int(g_match.group(2)),
            )
            rank = (path.stat().st_mtime_ns, path.name)
            previous_rank = (
                (newest[key].stat().st_mtime_ns, newest[key].name)
                if key in newest
                else None
            )
            if previous_rank is None or rank > previous_rank:
                newest[key] = path

    results: dict[Key, tuple[dict[int, int], Path]] = {}
    for key, path in newest.items():
        values: dict[int, int] = {}
        try:
            with _csv_source(path) as handle:
                for row in csv.reader(handle):
                    match = (
                        S_FILE_RE.fullmatch(Path(row[0].strip()).name)
                        if len(row) == 2
                        else None
                    )
                    if match is None or row[1].strip() not in {"0", "1"}:
                        raise ValueError(
                            f"Invalid Subgraph_Counts row in {path}: {row}"
                        )
                    index = int(match.group(1))
                    if index in values:
                        raise ValueError(f"Duplicate S_{index} in {path}")
                    values[index] = int(row[1])
        except FileNotFoundError:
            continue
        results[key] = (values, path)
    return results


def read_pattern_finder(
    root: Path,
) -> dict[Key, tuple[dict[int, int | None], Path]]:
    """Load first-not-found sizes for every VISTA configuration."""
    results: dict[Key, tuple[dict[int, int | None], Path]] = {}
    pattern = "results_queris_*_deg_*/recovery_result_*_deg_*/first_not_found.csv"
    for path in root.glob(pattern):
        s_match = S_PATTERN_RE.fullmatch(path.parent.parent.name)
        g_match = G_PATTERN_RE.fullmatch(path.parent.name)
        if s_match is None or g_match is None:
            continue
        key = (
            s_match.group(1),
            int(s_match.group(2)),
            g_match.group(1),
            int(g_match.group(2)),
        )
        values: dict[int, int | None] = {}
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                match = S_FILE_RE.fullmatch(row.get("S_NAME", "").strip())
                if match is None:
                    raise ValueError(f"Invalid VISTA row in {path}: {row}")
                index = int(match.group(1))
                if index in values:
                    raise ValueError(f"Duplicate S_{index} in {path}")
                raw_size = row.get("first_not_found_size", "").strip()
                values[index] = int(raw_size) if raw_size else None
        results[key] = (values, path)
    return results


def build_points(graphlets_root: Path, pattern_root: Path, max_k: int):
    """Build comparison records for all available configurations."""
    graphlets = read_graphlets(graphlets_root)
    patterns = read_pattern_finder(pattern_root)
    excluded: list[Key] = []
    points = []
    for key in sorted(set(graphlets) & set(patterns)):
        graphlet_values = graphlets[key][0]
        vista_values = patterns[key][0]
        if graphlet_values.keys() != vista_values.keys():
            raise ValueError(f"S IDs differ between methods for {key}")
        subgraph_counts_remaining = sum(
            value == 0 for value in graphlet_values.values()
        )
        for k in range(1, max_k + 1):
            vista_remaining = sum(
                size is None or size > k for size in vista_values.values()
            )
            points.append(
                (key, k, vista_remaining, subgraph_counts_remaining)
            )
    return points, excluded


def read_recovered_count_series(
    max_k: int, path: Path = DEFAULT_RECOVERED_COUNTS
) -> dict[Key, CountSeries]:
    """Read aggregate results recovered from completed experiment logs.

    These rows are used when the original per-query CSV was not recovered.
    Keeping the values in a separate, human-readable file avoids fabricating
    per-query outcomes for queries whose individual rows are unavailable.
    """
    if not path.is_file():
        return {}
    recovered: dict[Key, CountSeries] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            key = (
                row["query_family"].strip(),
                int(row["query_degree"]),
                row["graph_family"].strip(),
                int(row["graph_degree"]),
            )
            vista = tuple(int(row[f"vista_k{k}"]) for k in range(1, max_k + 1))
            recovered[key] = (int(row["subgraph_counts_remaining"]), vista)
    return recovered


def build_count_series(
    graphlets_root: Path, pattern_root: Path, max_k: int
) -> dict[Key, CountSeries]:
    """Return remaining-query counts, with recovered aggregates as overrides."""
    graphlets = read_graphlets(graphlets_root)
    patterns = read_pattern_finder(pattern_root)
    series: dict[Key, CountSeries] = {}
    for key in sorted(set(graphlets) & set(patterns)):
        graphlet_values = graphlets[key][0]
        vista_values = patterns[key][0]
        if graphlet_values.keys() != vista_values.keys():
            raise ValueError(f"S IDs differ between methods for {key}")
        graphlet_remaining = sum(value == 0 for value in graphlet_values.values())
        vista_remaining = tuple(
            sum(size is None or size > k for size in vista_values.values())
            for k in range(1, max_k + 1)
        )
        series[key] = (graphlet_remaining, vista_remaining)

    # A recovered row deliberately supersedes stale raw files if both exist.
    series.update(read_recovered_count_series(max_k))
    return series
