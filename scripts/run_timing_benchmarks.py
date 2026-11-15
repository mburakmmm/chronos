#!/usr/bin/env python3
"""Run timing-sensitive Chronos integration benchmarks without timing gates."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
NOXC = os.environ.get("NOXC", "noxc")
BACKENDS = ("llvm", "qbe")
SOURCE = "benchmarks/timing_benchmark.nox"
EXPECTED_METRICS = {
    "wake_latency",
    "fixed_rate_lateness",
    "fixed_rate_anchor_drift",
    "callback_raw_duration",
    "callback_event_duration",
}
TIMING_LINE = re.compile(
    r"^TIMING ([a-z_]+) (\d+) (\d+) (-?\d+) (-?\d+) (-?\d+)$"
)


def display_command(arguments: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def run(arguments: list[str]) -> str:
    print(f"+ {display_command(arguments)}", flush=True)
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    output = completed.stdout.strip()
    if completed.returncode != 0:
        if output:
            print(output, file=sys.stderr)
        raise RuntimeError(
            f"command failed with exit code {completed.returncode}: "
            f"{display_command(arguments)}"
        )
    return output


def report(backend: str, output: str) -> None:
    observed: set[str] = set()
    for line in output.splitlines():
        match = TIMING_LINE.fullmatch(line.strip())
        if match is None:
            if line.strip():
                print(line)
            continue
        name, sample_count, requested_ms, total_ms, minimum_ms, maximum_ms = (
            match.groups()
        )
        if name in observed:
            raise RuntimeError(f"duplicate timing metric from {backend}: {name}")
        observed.add(name)
        samples = int(sample_count)
        if samples < 1:
            raise RuntimeError(f"timing metric has no samples: {name}")
        average_ms = int(total_ms) / samples
        print(
            f"{backend:4} {name:27} samples={sample_count:>3} "
            f"requested_ms={requested_ms:>3} average_ms={average_ms:>7.3f} "
            f"min_ms={minimum_ms:>4} max_ms={maximum_ms:>4}"
        )
    if observed != EXPECTED_METRICS:
        missing = sorted(EXPECTED_METRICS - observed)
        extra = sorted(observed - EXPECTED_METRICS)
        raise RuntimeError(
            f"unexpected timing metrics from {backend}; missing={missing}, extra={extra}"
        )


def main() -> int:
    print(run([NOXC, "version"]))
    for backend in BACKENDS:
        report(backend, run([NOXC, "run", "--backend", backend, SOURCE]))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"timing benchmark failed: {error}", file=sys.stderr)
        raise SystemExit(1)
