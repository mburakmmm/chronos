#!/usr/bin/env python3
"""Verify the optional SQLite primitives used by Chronos persistence work."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NOXC = os.environ.get("NOXC", "noxc")
CASES = (
    (
        "proofs/persistence/sqlite_transaction_probe.nox",
        "1\njob-one\nTrue\n1\nTrue\na:3",
    ),
    (
        "proofs/persistence/sqlite_store_integration.nox",
        "sqlite-store-ok",
    ),
    ("examples/persistence/sqlite_definitions.nox", "reports.daily daily-summary"),
)


def display(arguments: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def run(arguments: list[str], env: dict[str, str] | None = None) -> str:
    print(f"+ {display(arguments)}", flush=True)
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    output = completed.stdout.strip()
    if completed.returncode != 0:
        if output:
            print(output, file=sys.stderr)
        raise RuntimeError(f"command failed: {display(arguments)}")
    return output


def main() -> int:
    version = run([NOXC, "version"])
    if "2.1.111" not in version:
        raise RuntimeError(f"persistence proof requires Nox 2.1.111, got: {version}")
    for source, expected in CASES:
        for backend in ("llvm", "qbe"):
            with tempfile.TemporaryDirectory(prefix="chronos-sqlite-") as directory:
                database = Path(directory) / "fixture.db"
                env = {**os.environ, "CHRONOS_SQLITE_TEST_DB": str(database)}
                output = run([NOXC, "run", "--backend", backend, source], env=env)
                if database.exists():
                    raise RuntimeError(f"SQLite proof left its database behind: {source}")
            if output != expected:
                raise RuntimeError(
                    f"unexpected {backend} output for {source}\n"
                    f"expected:\n{expected}\nactual:\n{output}"
                )
            print(f"  PASS {source} ({backend})", flush=True)
    print("Verified SQLite primitives and the single-owner Chronos adapter on LLVM/QBE.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"persistence verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
