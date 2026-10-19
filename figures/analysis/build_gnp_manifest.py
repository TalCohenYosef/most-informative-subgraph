#!/usr/bin/env python3
"""Build the checksum manifest for the fixed synthetic GNP benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

BACKGROUND_RE = re.compile(r"G_(average|rare|uniform)_deg_(3|5|8|15)\.json")
QUERY_DIR_RE = re.compile(r"input_color_(average|rare|uniform)_deg_(3|5|8|15)")
QUERY_RE = re.compile(r"S_([1-9][0-9]*)\.json")


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def records(dataset_root: Path):
    for path in sorted((dataset_root / "graphs_deg_5").glob("G_*.json")):
        match = BACKGROUND_RE.fullmatch(path.name)
        if match:
            yield path, "background", match.group(1), int(match.group(2)), ""
    for directory in sorted(dataset_root.glob("input_color_*_deg_*")):
        match = QUERY_DIR_RE.fullmatch(directory.name)
        if not match:
            continue
        for path in sorted(directory.glob("S_*.json")):
            query_match = QUERY_RE.fullmatch(path.name)
            if query_match:
                yield path, "query", match.group(1), int(match.group(2)), int(query_match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = list(records(args.dataset_root.resolve()))
    if len(rows) != 12012:
        raise ValueError(f"Expected 12,012 benchmark files; found {len(rows)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("relative_path", "role", "color_family", "target_degree", "query_id", "vertices", "edges", "bytes", "sha256"))
        for path, role, family, degree, query_id in rows:
            with path.open() as graph_handle:
                graph = json.load(graph_handle)
            writer.writerow(
                (
                    path.relative_to(args.dataset_root.resolve()).as_posix(),
                    role,
                    family,
                    degree,
                    query_id,
                    len(graph["nodes"]),
                    len(graph["links"]),
                    path.stat().st_size,
                    digest(path),
                )
            )
    print(f"Wrote {len(rows)} records to {args.output}")


if __name__ == "__main__":
    main()
