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
    ("examples/persistence/dispatch_once.nox", "reports.daily daily-summary\nsucceeded\ndisabled"),
)


def display(arguments: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def run(arguments: list[str], env: dict[str, str] | None = None, expected_status: int = 0) -> str:
    print(f"+ {display(arguments)}", flush=True)
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        timeout=90,
    )
    output = completed.stdout.strip()
    if completed.returncode != expected_status:
        if output:
            print(output, file=sys.stderr)
        raise RuntimeError(f"expected exit {expected_status}, got {completed.returncode}: {display(arguments)}")
    return output


def verify_once_restart(backend: str) -> None:
    effect = "once:1000:1:public\n"
    scenarios = (
        ("before-write", 71, "", "", "succeeded 2 False 1100", effect),
        ("before-commit", 74, "", "", "succeeded 2 False 1100", effect),
        ("after-commit", 72, "", "", "disabled 2 False 1050", ""),
        ("after-effect", 73, "", effect, "disabled 2 False 1050", effect),
        ("handler-error", 0, "handler-failed 2 False 1050", effect, "disabled 2 False 1050", effect),
        ("skip", 0, "skipped 2 False 1050", "", "disabled 2 False 1050", ""),
    )
    with tempfile.TemporaryDirectory(prefix="chronos-once-restart-") as directory:
        root = Path(directory)
        executable = root / "worker"
        run([NOXC, "build", "--backend", backend, "-o", str(executable), "proofs/persistence/once_restart_worker.nox"])
        for mode, status, output, initial_effect, restart, final_effect in scenarios:
            database = root / f"{mode}.db"
            effects = root / f"{mode}.effects"
            command = [str(executable), str(database), str(effects)]
            run([*command, "init-skip" if mode == "skip" else "init"])
            pending = run([*command, "poll", "999"])
            if pending != "pending 1 True 200" or effects.exists():
                raise RuntimeError(f"{backend}/{mode}: polling before the deadline changed state")
            initial = run([*command, mode, "1050"], expected_status=status)
            observed = effects.read_text() if effects.exists() else ""
            if initial != output or observed != initial_effect:
                raise RuntimeError(f"{backend}/{mode}: unexpected state at interruption")
            recovered = run([*command, "poll", "1100"])
            observed = effects.read_text() if effects.exists() else ""
            if recovered != restart or observed != final_effect:
                raise RuntimeError(f"{backend}/{mode}: unexpected state after reopening")
            again = run([*command, "poll", "1200"])
            if not again.startswith("disabled 2 False ") or (effects.read_text() if effects.exists() else "") != final_effect:
                raise RuntimeError(f"{backend}/{mode}: consumed job dispatched again")
            print(f"  PASS restart {mode} ({backend})", flush=True)


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
    for backend in ("llvm", "qbe"):
        verify_once_restart(backend)
    print("Verified SQLite primitives, definition storage and one-shot restart on LLVM/QBE.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"persistence verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
