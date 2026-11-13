#!/usr/bin/env python3
"""Run Chronos's portable release-quality verification matrix."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
NOXC = os.environ.get("NOXC", "noxc")
BACKENDS = ("llvm", "qbe")
FREESTANDING_MODULES = (
    "clock.nox",
    "cron.nox",
    "errors.nox",
    "events.nox",
    "executor.nox",
    "job.nox",
    "policy.nox",
    "registry.nox",
    "scheduler.nox",
    "time.nox",
    "trigger.nox",
)
PROOF_EXPECTATIONS = {
    "proofs/background_command_model.nox": "7",
    "proofs/concurrency_model.nox": "5\ntask failed\ncancelled at await\n49995000",
    "proofs/scheduler_sleep_probe.nox": "fast sleeper",
}


def display_command(arguments: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def run(arguments: list[str], expected_output: str | None = None) -> str:
    print(f"+ {display_command(arguments)}", flush=True)
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = completed.stdout.strip()
    if completed.returncode != 0:
        if output:
            print(output, file=sys.stderr)
        raise RuntimeError(
            f"command failed with exit code {completed.returncode}: "
            f"{display_command(arguments)}"
        )
    if expected_output is not None and output != expected_output:
        raise RuntimeError(
            f"unexpected output from {display_command(arguments)}\n"
            f"expected:\n{expected_output}\nactual:\n{output}"
        )
    print("  PASS", flush=True)
    return output


def sources(directory: str, pattern: str) -> list[Path]:
    return sorted((ROOT / directory).glob(pattern))


def relative(source: Path) -> str:
    return source.relative_to(ROOT).as_posix()


def main() -> int:
    version_output = run([NOXC, "version"])
    if "2.1.111" not in version_output:
        raise RuntimeError(f"Chronos CI requires Nox 2.1.111, got: {version_output}")

    test_sources = sources("tests", "*_test.nox")
    example_sources = sources("examples", "*.nox")
    if len(test_sources) != 18:
        raise RuntimeError(f"expected 18 test programs, found {len(test_sources)}")
    if len(example_sources) != 16:
        raise RuntimeError(f"expected 16 examples, found {len(example_sources)}")

    aggregate = run([NOXC, "test", "tests"])
    if "18 passed, 0 failed" not in aggregate:
        raise RuntimeError("aggregate test output did not report 18 passed, 0 failed")

    for backend in BACKENDS:
        for source in test_sources:
            run([NOXC, "run", "--backend", backend, relative(source)])
        for source in example_sources:
            run([NOXC, "run", "--backend", backend, relative(source)])
        for proof, expected in PROOF_EXPECTATIONS.items():
            run([NOXC, "run", "--backend", backend, proof], expected)

    for module in FREESTANDING_MODULES:
        run([NOXC, "check", "--profile", "freestanding", module])
    run([NOXC, "check", "system_clock.nox"])

    print(
        "Verified "
        f"{len(test_sources)} tests, {len(example_sources)} examples, "
        f"{len(PROOF_EXPECTATIONS)} concurrency proofs, and "
        f"{len(FREESTANDING_MODULES)} freestanding modules on both backends."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
