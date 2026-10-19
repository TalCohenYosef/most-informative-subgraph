#!/usr/bin/env python3
"""Write SHA-256 checksums for every tracked reproducibility artifact."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve()
    output = args.output.resolve()
    excluded_directories = {
        ".git",
        ".conda-env",
        ".conda-pkgs",
        ".external",
        ".validation",
        "__pycache__",
    }
    # These payloads are present in some working copies but intentionally
    # excluded from ordinary Git. The original GNP and raw real-world payloads
    # are not publication artifacts; generated replacements are also ignored.
    excluded_payload_roots = {
        Path("data/generated/gnp/references"),
        Path("data/generated/gnp/queries"),
        Path("data/raw/realworld"),
    }

    def included(path: Path) -> bool:
        relative = path.relative_to(repository)
        if excluded_directories.intersection(relative.parts):
            return False
        if path.resolve() == output:
            return False
        return not any(
            relative.is_relative_to(root) and relative.name != ".gitkeep"
            for root in excluded_payload_roots
        )

    files = sorted(
        path for path in repository.rglob("*")
        if path.is_file()
        and included(path)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for path in files:
            handle.write(f"{digest(path)}  {path.relative_to(repository).as_posix()}\n")
    print(f"Wrote checksums for {len(files)} files to {output}")


if __name__ == "__main__":
    main()
