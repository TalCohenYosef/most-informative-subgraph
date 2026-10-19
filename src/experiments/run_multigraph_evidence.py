#!/usr/bin/env python3
"""Mine shared patterns from one S library and save compact elimination results.

Example (preview only):
  python3 run_multigraph_evidence.py --alive-percent 0.015 --patterns 130 --dry-run

By default each run receives a new output directory.  An interrupted
checkpointed run can be continued in place with ``--resume-dir``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


BASE = Path(__file__).resolve().parent
REPOSITORY_ROOT = BASE.parents[1]
SGF_BUILD = Path(os.environ.get("SGF_BUILD_DIR", REPOSITORY_ROOT / ".external" / "subgraph_filter_suit" / "build"))
FINDER = SGF_BUILD / "sgf-pattern-finder"
SEARCHER = SGF_BUILD / "sgf-graph-searcher"
DEFAULT_BENCHMARK_ROOT = REPOSITORY_ROOT / "data" / "generated" / "gnp" / "files"
DEFAULT_S_DIR = DEFAULT_BENCHMARK_ROOT / "input_color_uniform_deg_8"
DEFAULT_G_DIR = DEFAULT_BENCHMARK_ROOT / "graphs_deg_5"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "data" / "results" / "vista_plus_new"
S_NAME_RE = re.compile(r"S_(\d+)\.json$")
G_NAME_RE = re.compile(r"G_.+\.json$")
LOAD_RE = re.compile(r"\[load\] index=(\d+) file=(.+)$")
MATCH_RE = re.compile(r"Matches found:\s*(\d+)")


def fraction(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("fraction must be a number in (0, 1]") from exc
    if not value.is_finite() or not 0 < value <= 1:
        raise argparse.ArgumentTypeError("fraction must be in (0, 1]")
    return value


def positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return value


def memory_limit(gigabytes: int):
    def set_limit() -> None:
        maximum = gigabytes * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
    return set_limit


def exact_match(pattern: Path, graph: Path, timeout_seconds: int,
                memory_gb: int) -> tuple[str, str]:
    command = [str(SEARCHER), "--subgraph-path", str(pattern),
               "--background-path", str(graph), "--reader-type", "json",
               "--prior-policy", "combined", "--stop-on-first-match"]
    try:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=timeout_seconds, check=False,
                                   preexec_fn=memory_limit(memory_gb))
    except subprocess.TimeoutExpired:
        return "timeout", f"exceeded {timeout_seconds}s"
    output = completed.stdout + completed.stderr
    match = MATCH_RE.search(output)
    if completed.returncode != 0 or match is None:
        return "error", output.strip()[:500]
    return ("present" if int(match.group(1)) > 0 else "absent"), output.strip()[:500]


def library_index_from_log(log_path: Path, expected: set[Path]) -> dict[int, Path]:
    mapping = {}
    expected_by_name = {path.name: path for path in expected}
    for line in log_path.read_text(errors="replace").splitlines():
        match = LOAD_RE.search(line)
        if match:
            index, loaded_path = int(match.group(1)), Path(match.group(2))
            if index in mapping:
                raise ValueError(f"Repeated library index {index} in {log_path}")
            file_path = expected_by_name.get(loaded_path.name)
            if file_path is None or loaded_path.resolve() != file_path.resolve():
                raise ValueError(f"Unexpected library file for index {index}: {loaded_path}")
            mapping[index] = file_path
    if set(mapping) != set(range(len(expected))) or set(mapping.values()) != expected:
        raise ValueError("Miner load log does not give an exact index-to-S mapping")
    return mapping


def pattern_index_from_csv(index_path: Path, library_size: int) -> dict[str, set[int]]:
    mapping: dict[str, set[int]] = defaultdict(set)
    with index_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != {"pattern_name", "graph_index"}:
            raise ValueError(f"Unexpected pattern index columns: {reader.fieldnames}")
        for row in reader:
            pattern_name = row["pattern_name"]
            index = int(row["graph_index"])
            if not 0 <= index < library_size:
                raise ValueError(f"Invalid graph index {index} for {pattern_name}")
            mapping[pattern_name].add(index)
    return dict(mapping)


def write_json_atomic(path: Path, value: object) -> None:
    """Replace a JSON checkpoint without leaving a partial file on interruption."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def numbered_pattern_files(pattern_dir: Path) -> list[Path]:
    pattern_files = sorted(pattern_dir.glob("pattern_*.json"))
    expected_names = [f"pattern_{index:04d}.json"
                      for index in range(len(pattern_files))]
    actual_names = [path.name for path in pattern_files]
    if actual_names != expected_names:
        raise ValueError(
            f"Patterns in {pattern_dir} are not a contiguous sequence from 0000"
        )
    return pattern_files


def apply_resume_config(args: argparse.Namespace, run_dir: Path) -> None:
    config_path = run_dir / "run_config.json"
    if not config_path.is_file():
        raise ValueError(f"Resume directory has no run_config.json: {run_dir}")
    config = json.loads(config_path.read_text())
    required = {
        "input_dir", "graph_dir", "alive_fraction", "patterns_requested",
        "miner_threads", "miner_batch_size", "max_pattern_vertices",
        "preprocess_timeout_seconds", "search_timeout_seconds",
        "miner_memory_gb", "search_memory_gb",
    }
    missing = required - set(config)
    if missing:
        raise ValueError(f"Resume config is missing keys: {sorted(missing)}")
    if config["miner_batch_size"] is None:
        raise ValueError("Only checkpointed mining runs can be resumed")
    args.input_dir = Path(config["input_dir"])
    args.graph_dir = Path(config["graph_dir"])
    args.alive_percent = fraction(str(config["alive_fraction"]))
    args.patterns = positive_int(str(config["patterns_requested"]))
    args.threads = positive_int(str(config["miner_threads"]))
    args.miner_batch_size = positive_int(str(config["miner_batch_size"]))
    args.max_pattern_vertices = positive_int(str(config["max_pattern_vertices"]))
    args.preprocess_timeout = positive_int(str(config["preprocess_timeout_seconds"]))
    args.search_timeout = positive_int(str(config["search_timeout_seconds"]))
    args.miner_memory_gb = positive_int(str(config["miner_memory_gb"]))
    args.search_memory_gb = positive_int(str(config["search_memory_gb"]))


def run(args: argparse.Namespace) -> Path | None:
    resuming = args.resume_dir is not None
    if resuming:
        run_dir = args.resume_dir.resolve()
        if not run_dir.is_dir():
            raise ValueError(f"Resume directory does not exist: {run_dir}")
        apply_resume_config(args, run_dir)
    s_dir = args.input_dir.resolve()
    g_dir = args.graph_dir.resolve()
    s_files = sorted((p.absolute() for p in s_dir.iterdir()
                      if p.is_file() and S_NAME_RE.fullmatch(p.name)),
                     key=lambda p: int(S_NAME_RE.fullmatch(p.name).group(1)))
    g_files = sorted(p.absolute() for p in g_dir.iterdir()
                     if p.is_file() and G_NAME_RE.fullmatch(p.name))
    if not s_files or not g_files:
        raise ValueError("Input must contain S_<number>.json and G_*.json files")
    if len({p.name for p in s_files}) != len(s_files):
        raise ValueError("Duplicate S names")
    if resuming:
        resume_config = json.loads((run_dir / "run_config.json").read_text())
        if resume_config.get("S_count") != len(s_files):
            raise ValueError("S input count changed since the interrupted run")
        if resume_config.get("G_count") != len(g_files):
            raise ValueError("G input count changed since the interrupted run")
    if not FINDER.is_file() or not SEARCHER.is_file():
        raise FileNotFoundError("Build sgf-pattern-finder and sgf-graph-searcher first")
    required_support = math.ceil(args.alive_percent * len(s_files))
    print(f"S inputs: {len(s_files)} from {s_dir}")
    print(f"G graphs: {len(g_files)} from {g_dir}")
    print(f"Alive fraction: {args.alive_percent}; minimum support: {required_support} S graphs")
    print(f"Patterns requested: {args.patterns}; miner threads: {args.threads}")
    if args.miner_batch_size:
        print(f"Checkpointed mining: {args.miner_batch_size} pattern(s) per miner process")
    print(f"Maximum pattern vertices: {args.max_pattern_vertices}")
    print(f"Memory caps: miner {args.miner_memory_gb} GiB; each exact search {args.search_memory_gb} GiB")
    print("Exact matching: every S for each pattern and every G; sequential and time-limited")
    if args.dry_run:
        if resuming:
            pattern_dir = run_dir / "patterns"
            saved = len(numbered_pattern_files(pattern_dir)) if pattern_dir.is_dir() else 0
            print(f"Resume directory: {run_dir}")
            print(f"Patterns already saved: {saved}/{args.patterns}")
        print("Dry run only: no experiment or output files changed")
        return None

    if resuming:
        if (run_dir / "timings.json").is_file():
            print(f"Run is already complete: {run_dir}")
            return run_dir
        pattern_dir = run_dir / "patterns"
        if not pattern_dir.is_dir():
            raise ValueError(f"Resume directory has no patterns directory: {run_dir}")
        print(f"Resuming existing experiment: {run_dir}", flush=True)
    else:
        args.output_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        label = str(args.alive_percent).replace(".", "p")
        run_dir = Path(tempfile.mkdtemp(
            prefix=f"{s_dir.name}_alive_{label}_patterns_{args.patterns}_{stamp}_",
            dir=args.output_root,
        )).resolve()
        pattern_dir = run_dir / "patterns"
        pattern_dir.mkdir()

        config = {
            "input_dir": str(s_dir), "graph_dir": str(g_dir),
            "S_count": len(s_files), "G_count": len(g_files),
            "alive_fraction": str(args.alive_percent),
            "required_support_count": required_support,
            "patterns_requested": args.patterns, "miner_threads": args.threads,
            "miner_batch_size": args.miner_batch_size,
            "max_pattern_vertices": args.max_pattern_vertices,
            "preprocess_timeout_seconds": args.preprocess_timeout,
            "search_timeout_seconds": args.search_timeout,
            "miner_memory_gb": args.miner_memory_gb,
            "search_memory_gb": args.search_memory_gb,
            "membership_mode": "exhaustive exact search over every S for every generated pattern",
            "meaning": "An S is eliminated for a G only when exact search confirms a pattern in S and absent from G.",
            "S_index_meaning": "S_i filename number (1-based)",
            "saved_outputs": ["G_summary.txt", "timings.json",
                              "pattern_to_S_indices.json",
                              "G_*/summary.json", "G_*/remaining_S_indices.json"],
        }
        write_json_atomic(run_dir / "run_config.json", config)

    miner_log = run_dir / "miner.log"
    checkpointed_mining = args.miner_batch_size is not None
    # The miner requires a folder; keep its symlinks only during mining.
    with tempfile.TemporaryDirectory(prefix="multigraph_library_",
                                     dir=run_dir.parent) as temporary_library:
        library_dir = Path(temporary_library)
        for source in s_files:
            (library_dir / source.name).symlink_to(source)
        print(f"Mining patterns; results in {run_dir}", flush=True)
        pattern_generation_started = time.perf_counter()
        if not checkpointed_mining:
            command = [str(FINDER), "--preprocess", "--reader-type", "json",
                       "--library-input-folder", str(library_dir),
                       "--output-folder", str(pattern_dir), "--pattern-output-type", "json",
                       "--preprocess-multigraph", str(args.patterns),
                       "--multigraph-alive-percent", str(args.alive_percent),
                       "--multigraph-max-pattern-vertices", str(args.max_pattern_vertices),
                       "--thread-number", str(args.threads), "--log-file-path", str(miner_log)]
            try:
                subprocess.run(command, check=True, timeout=args.preprocess_timeout,
                               preexec_fn=memory_limit(args.miner_memory_gb))
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"Pattern mining exceeded {args.preprocess_timeout}s; see {run_dir}"
                ) from exc
            library_index_from_log(miner_log, set(s_files))
        else:
            batch_root = run_dir / "miner_batches"
            batch_root.mkdir(exist_ok=True)
            generated = len(numbered_pattern_files(pattern_dir))
            if generated > args.patterns:
                raise ValueError(
                    f"Resume directory has {generated} patterns; expected at most "
                    f"{args.patterns}"
                )
            existing_batch_numbers = []
            for existing_batch in batch_root.iterdir():
                match = re.fullmatch(r"batch_(\d+)", existing_batch.name)
                if existing_batch.is_dir() and match:
                    existing_batch_numbers.append(int(match.group(1)))
            batch_number = max(existing_batch_numbers, default=-1) + 1
            if generated:
                print(f"Found mining checkpoint: {generated}/{args.patterns} patterns", flush=True)
            while generated < args.patterns:
                batch_count = min(args.miner_batch_size, args.patterns - generated)
                batch_dir = batch_root / f"batch_{batch_number:04d}"
                batch_dir.mkdir()
                batch_log = batch_dir / "miner.log"
                command = [str(FINDER), "--preprocess", "--reader-type", "json",
                           "--library-input-folder", str(library_dir),
                           "--output-folder", str(batch_dir), "--pattern-output-type", "json",
                           "--preprocess-multigraph", str(batch_count),
                           "--multigraph-alive-percent", str(args.alive_percent),
                           "--multigraph-max-pattern-vertices", str(args.max_pattern_vertices),
                           "--thread-number", str(min(args.threads, batch_count)),
                           "--log-file-path", str(batch_log)]
                print(f"Mining checkpoint batch {batch_number + 1}: "
                      f"{generated}/{args.patterns} patterns saved", flush=True)
                try:
                    subprocess.run(command, check=True, timeout=args.preprocess_timeout,
                                   preexec_fn=memory_limit(args.miner_memory_gb))
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError(
                        f"Mining batch {batch_number + 1} exceeded "
                        f"{args.preprocess_timeout}s; see {batch_dir}"
                    ) from exc
                library_index_from_log(batch_log, set(s_files))
                batch_patterns = sorted(batch_dir.glob("pattern_*.json"))
                if len(batch_patterns) != batch_count:
                    raise ValueError(
                        f"Batch {batch_number + 1} produced {len(batch_patterns)} patterns; "
                        f"expected {batch_count}"
                    )
                for source_pattern in batch_patterns:
                    target_name = f"pattern_{generated:04d}.json"
                    shutil.move(str(source_pattern), pattern_dir / target_name)
                    generated += 1
                write_json_atomic(run_dir / "mining_progress.json", {
                    "patterns_requested": args.patterns,
                    "patterns_saved": generated,
                    "last_completed_batch": batch_number + 1,
                    "last_completed_batch_dir": batch_dir.name,
                })
                print(f"Checkpoint saved: {generated}/{args.patterns} patterns", flush=True)
                batch_number += 1
        pattern_generation_seconds = time.perf_counter() - pattern_generation_started
    index_files = sorted(pattern_dir.glob("pattern_index_*.csv"))
    if checkpointed_mining:
        pattern_members = {}
    else:
        if len(index_files) != 1:
            raise ValueError(f"Expected one pattern index in {pattern_dir}; got {index_files}")
        pattern_members = pattern_index_from_csv(index_files[0], len(s_files))
    pattern_files = numbered_pattern_files(pattern_dir)
    if not pattern_files:
        raise ValueError(f"No pattern JSON files written to {pattern_dir}")
    if len(pattern_files) < args.patterns:
        print(f"WARNING: requested {args.patterns} patterns, but miner produced "
              f"only {len(pattern_files)}", file=sys.stderr, flush=True)
    if set(pattern_members) - {path.name for path in pattern_files}:
        raise ValueError("Pattern index references a missing pattern JSON file")
    for pattern_path in pattern_files:
        pattern_members.setdefault(pattern_path.name, set())

    pattern_index_summary = {}
    verified_members: dict[str, list[Path]] = {}
    eligible_patterns = []
    s_by_index = {
        int(S_NAME_RE.fullmatch(path.name).group(1)): path for path in s_files
    }
    verification_root = run_dir / "S_verification_checkpoints"
    verification_root.mkdir(exist_ok=True)
    s_verification_seconds = 0.0
    for pattern_name in sorted(pattern_members):
        pattern_path = pattern_dir / pattern_name
        if not pattern_path.is_file():
            raise FileNotFoundError(pattern_path)
        checkpoint_path = verification_root / pattern_name
        if checkpoint_path.is_file():
            checkpoint = json.loads(checkpoint_path.read_text())
            if checkpoint.get("pattern_name") != pattern_name:
                raise ValueError(f"Invalid verification checkpoint: {checkpoint_path}")
            confirmed_indices = checkpoint.get("S_indices")
            unresolved_indices = checkpoint.get("unresolved_S_indices")
            if (not isinstance(confirmed_indices, list)
                    or not isinstance(unresolved_indices, list)
                    or not set(confirmed_indices).issubset(s_by_index)
                    or not set(unresolved_indices).issubset(s_by_index)):
                raise ValueError(f"Invalid S indices in checkpoint: {checkpoint_path}")
            elapsed = float(checkpoint.get("search_seconds", 0.0))
            print(f"Reusing S checkpoint for {pattern_name}", flush=True)
        else:
            verification_started = time.perf_counter()
            confirmed_indices = []
            unresolved_indices = []
            for s_path in s_files:
                status, _ = exact_match(pattern_path, s_path, args.search_timeout,
                                        args.search_memory_gb)
                s_index = int(S_NAME_RE.fullmatch(s_path.name).group(1))
                if status in {"timeout", "error"}:
                    unresolved_indices.append(s_index)
                if status == "present":
                    confirmed_indices.append(s_index)
            elapsed = time.perf_counter() - verification_started
            write_json_atomic(checkpoint_path, {
                "pattern_name": pattern_name,
                "S_indices": sorted(confirmed_indices),
                "unresolved_S_indices": sorted(unresolved_indices),
                "search_seconds": round(elapsed, 6),
            })
        confirmed = [s_by_index[index] for index in confirmed_indices]
        s_verification_seconds += elapsed
        verified_members[pattern_name] = confirmed
        eligible = len(confirmed) >= required_support and not unresolved_indices
        if eligible:
            eligible_patterns.append(pattern_name)
        pattern_index_summary[pattern_name] = {
            "S_indices": sorted(confirmed_indices),
            "unresolved_S_indices": sorted(unresolved_indices),
            "meets_alive_threshold": eligible,
        }
        print(f"{pattern_name}: {len(confirmed)} exact S matches; "
              f"unresolved={len(unresolved_indices)}; eligible={eligible}", flush=True)
    write_json_atomic(run_dir / "pattern_to_S_indices.json", {
        "index_meaning": "S_i filename number (1-based, not miner graph_index)",
        "patterns": pattern_index_summary,
    })

    witnesses: dict[tuple[str, str], set[str]] = defaultdict(set)
    incomplete_G_checks: dict[str, int] = defaultdict(int)
    g_search_seconds_by_name: dict[str, float] = defaultdict(float)
    g_checkpoint_root = run_dir / "G_search_checkpoints"
    g_checkpoint_root.mkdir(exist_ok=True)
    g_checkpoints: dict[str, dict] = {}
    for g_path in g_files:
        checkpoint_path = g_checkpoint_root / f"{g_path.stem}.json"
        if checkpoint_path.is_file():
            checkpoint = json.loads(checkpoint_path.read_text())
            if (checkpoint.get("G_name") != g_path.stem
                    or not isinstance(checkpoint.get("pattern_checks"), dict)):
                raise ValueError(f"Invalid G checkpoint: {checkpoint_path}")
            g_checkpoints[g_path.stem] = checkpoint
        else:
            g_checkpoints[g_path.stem] = {
                "G_name": g_path.stem,
                "pattern_checks": {},
            }
    for pattern_name in eligible_patterns:
        pattern_path = pattern_dir / pattern_name
        for g_path in g_files:
            checkpoint = g_checkpoints[g_path.stem]
            pattern_checks = checkpoint["pattern_checks"]
            if pattern_name in pattern_checks:
                check = pattern_checks[pattern_name]
                status = check.get("status")
                if status not in {"present", "absent", "timeout", "error"}:
                    raise ValueError(
                        f"Invalid status for {pattern_name} in {g_path.stem} checkpoint"
                    )
                elapsed = float(check.get("search_seconds", 0.0))
                print(f"Reusing G checkpoint: {pattern_name} vs {g_path.stem}: "
                      f"{status}", flush=True)
            else:
                single_search_started = time.perf_counter()
                status, _ = exact_match(pattern_path, g_path, args.search_timeout,
                                        args.search_memory_gb)
                elapsed = time.perf_counter() - single_search_started
                pattern_checks[pattern_name] = {
                    "status": status,
                    "search_seconds": round(elapsed, 6),
                }
                write_json_atomic(g_checkpoint_root / f"{g_path.stem}.json", checkpoint)
                print(f"{pattern_name} vs {g_path.stem}: {status}", flush=True)
            g_search_seconds_by_name[g_path.stem] += elapsed
            if status in {"timeout", "error"}:
                incomplete_G_checks[g_path.stem] += 1
            if status == "absent":
                for s_path in verified_members[pattern_name]:
                    witnesses[(s_path.stem, g_path.stem)].add(pattern_name)
    g_search_seconds = sum(g_search_seconds_by_name.values())
    summary_lines = []
    for g_path in g_files:
        g_dir = run_dir / g_path.stem
        g_dir.mkdir(exist_ok=True)
        remaining_indices = []
        undetermined_indices = []
        for s_path in s_files:
            matched_witnesses = sorted(witnesses[(s_path.stem, g_path.stem)])
            if not matched_witnesses:
                s_index = int(S_NAME_RE.fullmatch(s_path.name).group(1))
                remaining_indices.append(s_index)
                if incomplete_G_checks[g_path.stem]:
                    undetermined_indices.append(s_index)
        eliminated = len(s_files) - len(remaining_indices)
        undetermined = len(undetermined_indices)
        g_summary = {
            "G_name": g_path.stem, "G_path": str(g_path),
            "total_S": len(s_files), "patterns_requested": args.patterns,
            "patterns_generated": len(pattern_files),
            "patterns_meeting_threshold": len(eligible_patterns),
            "eliminated_S": eliminated,
            "eliminated_percent": round(100 * eliminated / len(s_files), 2),
            "not_eliminated_by_generated_patterns": len(s_files) - eliminated - undetermined,
            "undetermined_S": undetermined,
            "incomplete_pattern_checks_on_G": incomplete_G_checks[g_path.stem],
            "G_search_seconds": round(g_search_seconds_by_name[g_path.stem], 6),
        }
        write_json_atomic(g_dir / "summary.json", g_summary)
        write_json_atomic(g_dir / "remaining_S_indices.json", {
            "index_meaning": "S_i filename number (1-based)",
            "remaining_S_indices": remaining_indices,
            "undetermined_S_indices": undetermined_indices,
        })
        line = (f"{g_path.stem}: {eliminated}/{len(s_files)} S eliminated "
                f"({undetermined} undetermined); G search "
                f"{g_search_seconds_by_name[g_path.stem]:.3f}s")
        summary_lines.append(line)
        print(line, flush=True)
    (run_dir / "G_summary.txt").write_text("\n".join(summary_lines) + "\n")
    timings = {
        "pattern_generation_seconds": round(pattern_generation_seconds, 6),
        "S_verification_seconds": round(s_verification_seconds, 6),
        "all_G_search_seconds": round(g_search_seconds, 6),
        "G_search_seconds": {
            g_path.stem: round(g_search_seconds_by_name[g_path.stem], 6)
            for g_path in g_files
        },
    }
    write_json_atomic(run_dir / "timings.json", timings)
    # Completion is marked by timings.json before intermediates are removed,
    # so an interruption never leaves an unresumable half-finalized run.
    shutil.rmtree(pattern_dir)
    shutil.rmtree(verification_root)
    shutil.rmtree(g_checkpoint_root)
    if miner_log.is_file():
        miner_log.unlink()
    print(f"Pattern generation time: {pattern_generation_seconds:.3f}s", flush=True)
    print(f"S verification time: {s_verification_seconds:.3f}s", flush=True)
    print(f"All G search time: {g_search_seconds:.3f}s", flush=True)
    print(f"Finished. Evidence directory: {run_dir}", flush=True)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_S_DIR,
                        help="One S library directory (default: Uniform-8)")
    parser.add_argument("--graph-dir", type=Path, default=DEFAULT_G_DIR,
                        help="Directory containing all G_*.json graphs")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--resume-dir", type=Path,
        help="Continue a checkpointed run in place, using its run_config.json",
    )
    parser.add_argument("--alive-percent", type=fraction, default=Decimal("0.03"),
                        help="Fraction of S graphs required per pattern, e.g. 0.03 for 3%%")
    parser.add_argument("--patterns", type=positive_int, default=30)
    parser.add_argument("--max-pattern-vertices", type=positive_int, default=20,
                        help="Stop growing each pattern at this many vertices (default: 20)")
    parser.add_argument("--threads", type=positive_int, default=2)
    parser.add_argument("--miner-batch-size", type=positive_int,
                        help="Mine this many patterns per subprocess and checkpoint each batch")
    parser.add_argument("--preprocess-timeout", type=positive_int, default=3600)
    parser.add_argument("--search-timeout", type=positive_int, default=120)
    parser.add_argument("--miner-memory-gb", type=positive_int, default=64)
    parser.add_argument("--search-memory-gb", type=positive_int, default=16)
    parser.add_argument("--dry-run", action="store_true", help="Show scope without running")
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
