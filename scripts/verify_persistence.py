#!/usr/bin/env python3
"""Verify the optional SQLite primitives used by Chronos persistence work."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
NOXC = os.environ.get("NOXC", "noxc")
SOURCE = "proofs/persistence/sqlite_transaction_probe.nox"
EXPECTED = "1\njob-one\nTrue\n1\nTrue"
PROBE_DATABASE = ROOT / ".chronos-sqlite-transaction-probe.db"


def display(arguments: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def run(arguments: list[str]) -> str:
    print(f"+ {display(arguments)}", flush=True)
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
        raise RuntimeError(f"command failed: {display(arguments)}")
    return output


def main() -> int:
    version = run([NOXC, "version"])
    if "2.1.111" not in version:
        raise RuntimeError(f"persistence proof requires Nox 2.1.111, got: {version}")
    for backend in ("llvm", "qbe"):
        output = run([NOXC, "run", "--backend", backend, SOURCE])
        if output != EXPECTED:
            raise RuntimeError(
                f"unexpected {backend} output\nexpected:\n{EXPECTED}\nactual:\n{output}"
            )
        if PROBE_DATABASE.exists():
            raise RuntimeError("SQLite proof did not remove its database")
        print(f"  PASS ({backend})", flush=True)
    print("Verified SQLite reopen, transactions, rollback, and parameter binding on LLVM/QBE.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"persistence verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
