#!/usr/bin/env python3
"""Verify the optional SQLite primitives used by Chronos persistence work."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NOXC = os.environ.get("NOXC", "noxc")
CASES = (
    (
        "proofs/persistence/sqlite_transaction_probe.nox",
        "1\njob-one\nTrue\n1\nTrue\n3 0 3",
    ),
    (
        "proofs/persistence/sqlite_store_integration.nox",
        "sqlite-store-ok",
    ),
    ("examples/persistence/sqlite_definitions.nox", "reports.daily daily-summary"),
    ("examples/persistence/dispatch_once.nox", "reports.daily daily-summary\nsucceeded\ndisabled"),
    ("examples/persistence/dispatch_cron.nox", "60000 summary\nsucceeded\npending\n240000 summary\nsucceeded"),
    ("proofs/persistence/persistent_scheduler_integration.nox", "persistent-scheduler-ok"),
    ("proofs/persistence/outcome_migration.nox", "outcome-migration-ok"),
    ("proofs/timezone/stored_local_cron_probe.nox", "zoned-cron-storage-ok"),
    ("examples/persistence/poll_zoned.nox", "report 1729989000000\nsucceeded\nreport 1729992600000\nsucceeded"),
    ("examples/persistence/poll_stored.nox", "pending\nreport.once summary\nsucceeded\nrecorded succeeded\nstopped"),
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


def verify_once_restart(backend: str, executable: Path) -> None:
    effect = "fixture:1000:1:public\n"
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


def verify_cron_restart(backend: str, executable: Path) -> None:
    first = "fixture:60000:1:public\n"
    next_effect = "fixture:240000:1:public\n"
    scenarios = (
        ("before-commit", 74, "", "", "succeeded 2 True 195000 240000|* * * * *", first),
        ("after-commit", 72, "", "", "pending 2 True 190000 240000|* * * * *", ""),
        ("after-effect", 73, "", first, "pending 2 True 190000 240000|* * * * *", first),
        ("skip", 0, "skipped 2 True 190000 240000|* * * * *", "", "pending 2 True 190000 240000|* * * * *", ""),
    )
    with tempfile.TemporaryDirectory(prefix="chronos-cron-restart-") as directory:
        root = Path(directory)
        for mode, status, output, initial_effect, restart, final_effect in scenarios:
            effects = root / f"{mode}.effects"
            command = [str(executable), str(root / f"{mode}.db"), str(effects)]
            run([*command, "init-skip" if mode == "skip" else "init", "0", "cron"])
            initial = run([*command, mode, "190000", "cron"], expected_status=status)
            if initial != output or (effects.read_text() if effects.exists() else "") != initial_effect:
                raise RuntimeError(f"{backend}/{mode}: unexpected cron state at interruption")
            recovered = run([*command, "poll", "195000", "cron"])
            if recovered != restart or (effects.read_text() if effects.exists() else "") != final_effect:
                raise RuntimeError(f"{backend}/{mode}: unexpected cron state after reopen")
            backward = run([*command, "poll", "60000", "cron"])
            if not backward.startswith("pending 2 True "):
                raise RuntimeError(f"{backend}/{mode}: backward clock replayed cron")
            following = run([*command, "poll", "240000", "cron"])
            if following != "succeeded 3 True 240000 300000|* * * * *" or effects.read_text() != final_effect + next_effect:
                raise RuntimeError(f"{backend}/{mode}: next cron occurrence did not dispatch exactly once")
            print(f"  PASS cron restart {mode} ({backend})", flush=True)
        effects = root / "invalid.effects"
        command = [str(executable), str(root / "invalid.db"), str(effects)]
        run([*command, "init-invalid", "0", "cron"])
        invalid = run([*command, "invalid", "190000", "cron"])
        if invalid != "stored cron cursor does not match its expression 1 True 200 60001|* * * * *" or effects.exists():
            raise RuntimeError(f"{backend}: invalid cron cursor changed state")


def verify_zoned_restart(backend: str, executable: Path) -> None:
    first = "1729989000000"
    second = "1729992600000"
    first_effect = f"fixture:{first}:1:public\n"
    second_effect = f"fixture:{second}:1:public\n"
    scenarios = (
        ("before-commit", 74, "succeeded", first_effect),
        ("after-commit", 72, "pending", ""),
        ("after-effect", 73, "pending", first_effect),
    )
    with tempfile.TemporaryDirectory(prefix="chronos-zoned-restart-") as directory:
        root = Path(directory)
        for mode, code, restart_status, effects_after_restart in scenarios:
            effects = root / f"{mode}.effects"
            command = [str(executable), str(root / f"{mode}.db"), str(effects)]
            run([*command, "init", "0", "zoned"])
            run([*command, mode, first, "zoned"], expected_status=code)
            recovered = run([*command, "poll", first, "zoned"])
            observed = effects.read_text() if effects.exists() else ""
            if recovered != f"{restart_status} 2 True {first}" or observed != effects_after_restart:
                raise RuntimeError(f"{backend}/{mode}: unexpected zoned state after reopen")
            following = run([*command, "poll", second, "zoned"])
            if following != f"succeeded 3 True {second}" or effects.read_text() != observed + second_effect:
                raise RuntimeError(f"{backend}/{mode}: second fold occurrence did not run once")
            print(f"  PASS zoned restart {mode} ({backend})", flush=True)


def verify_secret_reference(backend: str) -> None:
    env_key = "CHRONOS_EXAMPLE_REPORT_TOKEN"
    token = "chronos-synthetic-runtime-credential-731e"
    with tempfile.TemporaryDirectory(prefix="chronos-runtime-secret-") as directory:
        root = Path(directory)
        executable = root / "secret-reference"
        run([NOXC, "build", "--backend", backend, "-o", str(executable), "examples/persistence/secret_reference.nox"])
        for mode, expected in (("present", "succeeded"), ("absent", "handler-failed"), ("empty", "handler-failed")):
            env = os.environ.copy()
            env.pop(env_key, None)
            if mode != "absent":
                env[env_key] = token if mode == "present" else ""
            database = root / f"{mode}.db"
            output = run([str(executable), str(database)], env=env)
            if output != expected:
                raise RuntimeError(f"{backend}/{mode}: unexpected credential example status")
            connection = sqlite3.connect(database)
            try:
                record = connection.execute("SELECT handler_config, enabled, revision FROM chronos_jobs").fetchall()
                outcome = connection.execute("SELECT status, revision FROM chronos_outcomes").fetchall()
            finally:
                connection.close()
            if record != [("reporting", 0, 2)] or outcome != [(expected, 2)]:
                raise RuntimeError(f"{backend}/{mode}: unexpected credential example records")
            if token.encode() in database.read_bytes():
                raise RuntimeError(f"{backend}/{mode}: synthetic runtime credential found in SQLite")
        print(f"  PASS runtime credential isolation ({backend})", flush=True)


def main() -> int:
    version = run([NOXC, "version"])
    if version != "noxc 2.2.70":
        raise RuntimeError(f"persistence proof requires Nox 2.2.70, got: {version}")
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
        with tempfile.TemporaryDirectory(prefix="chronos-restart-worker-") as directory:
            executable = Path(directory) / "worker"
            run([NOXC, "build", "--backend", backend, "-o", str(executable), "proofs/persistence/restart_worker.nox"])
            verify_once_restart(backend, executable)
            verify_cron_restart(backend, executable)
            verify_zoned_restart(backend, executable)
        verify_secret_reference(backend)
    print("Verified SQLite definition storage and UTC one-shot, UTC cron and zoned cron restart on LLVM/QBE.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"persistence verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
