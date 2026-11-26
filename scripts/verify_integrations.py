#!/usr/bin/env python3
"""Verify optional framework examples without coupling frameworks to core."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NOXC = os.environ.get("NOXC", "noxc")
NOX_VERSION = "2.2.70"
BACKENDS = ("llvm", "qbe")
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
        timeout=180,
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


def prepare_package(destination: Path) -> str:
    destination.mkdir()
    for source in (*ROOT.glob("*.nox"), ROOT / "nox.json"):
        shutil.copy2(source, destination / source.name)
    (destination / "examples").mkdir()
    shutil.copy2(ROOT / "examples" / "poll.nox", destination / "examples" / "poll.nox")
    run(["git", "init", "-b", "main"], destination)
    run(["git", "add", "."], destination)
    run(["git", "-c", "user.name=Chronos Tests", "-c", "user.email=tests@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-m", "Chronos package fixture"], destination)
    return run(["git", "rev-parse", "HEAD"], destination)


def dependency(alias: str, package: Path, revision: str) -> dict:
    return {"alias": alias, "repo": str(package), "ref": revision, "require_signed_commit": False}


def write_manifest(workspace: Path, manifest: dict) -> None:
    (workspace / "nox.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")


def verify_lock(workspace: Path, expected: dict[str, str]) -> None:
    packages = json.loads((workspace / "nox.lock").read_text(encoding="utf-8"))["packages"]
    for alias, revision in expected.items():
        if [item["resolved"] for item in packages if item["alias"] == alias] != [revision]:
            raise RuntimeError(f"unexpected dependency resolution for {alias}")


def prepare_workspace(name: str, destination: Path, package: Path, revision: str) -> None:
    source = ROOT / "integrations" / name
    shutil.copy2(source / "main.nox", destination / "main.nox")
    shutil.copy2(source / "nox.lock", destination / "nox.lock")
    manifest = json.loads((source / "nox.json").read_text(encoding="utf-8"))
    manifest["requires"].append(dependency("chronos", package, revision))
    write_manifest(destination, manifest)


def verify_consumer(workspace: Path, alias: str, package: Path, revision: str) -> None:
    workspace.mkdir()
    write_manifest(workspace, {"name": "chronos_consumer", "entry": "main.nox",
                               "requires": [dependency(alias, package, revision)]})
    examples = (
        ("poll.nox", "main.nox", "before 0\nran notify.once scheduled 1250\nafter 1 True"),
        ("cron_utc.nox", "cron_demo.nox", "2024-01-01 09:00:00 UTC\n2024-02-29 00:00:00 UTC"),
    )
    for source, filename, _ in examples:
        snippet = (ROOT / "examples" / source).read_text(encoding="utf-8")
        (workspace / filename).write_text(snippet.replace("from chronos.", f"from {alias}."), encoding="utf-8")
    run([NOXC, "fetch"], workspace)
    verify_lock(workspace, {alias: revision})
    for backend in BACKENDS:
        for _, filename, expected in examples:
            run([NOXC, "run", "--backend", backend, filename], workspace, expected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-alias", help="run only the standalone consumer with the given alias")
    options = parser.parse_args()
    version = run([NOXC, "version"], ROOT)
    if version != f"noxc {NOX_VERSION}":
        raise RuntimeError(
            f"framework integrations require Nox {NOX_VERSION}, got: {version}"
        )

    with tempfile.TemporaryDirectory(prefix="chronos-package-test-") as temporary:
        root = Path(temporary)
        package = root / "package"
        revision = prepare_package(package)
        if options.consumer_alias:
            verify_consumer(root / "consumer", options.consumer_alias, package, revision)
            return 0
        verify_consumer(root / "consumer", "chronos", package, revision)
        for name, resolved, expected_output in INTEGRATIONS:
            workspace = root / name
            workspace.mkdir()
            prepare_workspace(name, workspace, package, revision)
            run([NOXC, "fetch"], workspace)
            verify_lock(workspace, {name: resolved, "chronos": revision})
            for backend in BACKENDS:
                run(
                    [NOXC, "run", "--backend", backend, "main.nox"],
                    workspace,
                    expected_output,
                )

    print(
        "Verified real Chronos package consumption and locked Nyx/Aether integrations on LLVM and QBE."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"integration verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
