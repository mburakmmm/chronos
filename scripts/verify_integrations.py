#!/usr/bin/env python3
"""Verify optional framework examples without coupling frameworks to core."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NOXC = os.environ.get("NOXC", "noxc")
NOX_VERSION = "2.1.186"
BACKENDS = ("llvm", "qbe")
CORE_SOURCES = (
    "clock.nox",
    "cron.nox",
    "errors.nox",
    "events.nox",
    "executor.nox",
    "job.nox",
    "policy.nox",
    "registry.nox",
    "scheduler.nox",
    "system_clock.nox",
    "time.nox",
    "trigger.nox",
)
CORE_MODULES = tuple(source.removesuffix(".nox") for source in CORE_SOURCES)
INTEGRATIONS = (
    (
        "nyx",
        "8acc737cadf58e5f7529e91e3838c095bce3c8ad",
        "chronos nyx integration ready",
    ),
    (
        "aether",
        "eef4664b5c7a2f9ec4c3bea19004f6bbebbdc001",
        "chronos aether integration ready",
    ),
)


def display_command(arguments: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def run(
    arguments: list[str],
    cwd: Path,
    expected_output: str | None = None,
) -> str:
    print(f"+ {display_command(arguments)}", flush=True)
    completed = subprocess.run(
        arguments,
        cwd=cwd,
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


def qualify_core_imports(source_text: str) -> str:
    lines: list[str] = []
    for line in source_text.splitlines(keepends=True):
        qualified = line
        for module in CORE_MODULES:
            if line.startswith(f"from {module} import "):
                qualified = line.replace(
                    f"from {module} import ",
                    f"from chronos.{module} import ",
                    1,
                )
                break
            if line == f"import {module}\n":
                qualified = f"import chronos.{module}\n"
                break
        lines.append(qualified)
    return "".join(lines)


def prepare_workspace(name: str, resolved: str, destination: Path) -> str:
    source = ROOT / "integrations" / name
    shutil.copy2(source / "main.nox", destination / "main.nox")
    shutil.copy2(source / "nox.json", destination / "nox.json")
    lock = source / "nox.lock"
    if not lock.exists():
        raise RuntimeError(f"missing dependency lock for {name}")
    lock_text = lock.read_text(encoding="utf-8")
    if resolved not in lock_text:
        raise RuntimeError(f"{name} lock does not contain expected commit {resolved}")
    shutil.copy2(lock, destination / "nox.lock")
    namespace = destination / "chronos"
    namespace.mkdir()
    for filename in CORE_SOURCES:
        source_text = (ROOT / filename).read_text(encoding="utf-8")
        (namespace / filename).write_text(
            qualify_core_imports(source_text),
            encoding="utf-8",
        )
    return lock_text


def main() -> int:
    version = run([NOXC, "version"], ROOT)
    if NOX_VERSION not in version:
        raise RuntimeError(
            f"framework integrations require Nox {NOX_VERSION}, got: {version}"
        )

    for name, resolved, expected_output in INTEGRATIONS:
        with tempfile.TemporaryDirectory(prefix=f"chronos-{name}-") as temporary:
            workspace = Path(temporary)
            locked = prepare_workspace(name, resolved, workspace)
            run([NOXC, "fetch"], workspace)
            if (workspace / "nox.lock").read_text(encoding="utf-8") != locked:
                raise RuntimeError(f"noxc fetch changed the pinned {name} lock")
            for backend in BACKENDS:
                run(
                    [NOXC, "run", "--backend", backend, "main.nox"],
                    workspace,
                    expected_output,
                )

    print(
        "Verified Nyx v0.29.0 and Aether v0.12.0 source-overlay "
        "integrations on LLVM and QBE."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"integration verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
