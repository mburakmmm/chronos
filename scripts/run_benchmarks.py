#!/usr/bin/env python3
"""Run Chronos benchmarks on LLVM and QBE without enforcing timing gates."""

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
BENCHMARKS = (
    "benchmarks/cron_benchmark.nox",
    "benchmarks/due_lookup_benchmark.nox",
)
BENCHMARK_LINE = re.compile(
    r"^BENCH ([a-z_]+) (\d+) (\d+) (\d+) (\d+) (-?\d+)$"
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
        timeout=600,
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


def report(backend: str, output: str) -> int:
    count = 0
    for line in output.splitlines():
        match = BENCHMARK_LINE.fullmatch(line.strip())
        if match is None:
            if line.strip():
                print(line)
            continue
        name, size, iterations, due_count, elapsed_ms, checksum = match.groups()
        elapsed = int(elapsed_ms)
        repeats = int(iterations)
        milliseconds_per_iteration = elapsed / repeats
        print(
            f"{backend:4} {name:16} size={size:>5} "
            f"due={due_count:>5} iterations={iterations:>6} "
            f"elapsed_ms={elapsed_ms:>6} "
            f"ms/iteration={milliseconds_per_iteration:>10.4f} "
            f"checksum={checksum}"
        )
        count += 1
    return count


def main() -> int:
    version = run([NOXC, "version"])
    print(version)
    expected_lines = 12
    for backend in BACKENDS:
        observed_lines = 0
        for benchmark in BENCHMARKS:
            observed_lines += report(
                backend,
                run([NOXC, "run", "--backend", backend, benchmark]),
            )
        if observed_lines != expected_lines:
            raise RuntimeError(
                f"expected {expected_lines} benchmark rows for {backend}, "
                f"found {observed_lines}"
            )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"benchmark failed: {error}", file=sys.stderr)
        raise SystemExit(1)
