#!/usr/bin/env python3
"""Compare canonical and renamed Git dependency imports on the installed Nox."""

import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


NOXC = os.environ.get("NOXC", "noxc")
PACKAGE_NAME = "alias_probe"
BACKENDS = ("llvm", "qbe")


def manifest(workspace, name, entry, dependencies):
    (workspace / "nox.json").write_text(
        json.dumps({"name": name, "entry": entry, "requires": dependencies}) + "\n",
        encoding="utf-8",
    )


def run(arguments, cwd, env, check=True):
    return subprocess.run(
        arguments, cwd=cwd, env=env, check=check, capture_output=True,
        text=True, timeout=30,
    )


def main():
    with TemporaryDirectory(prefix="nox-package-alias-") as directory:
        root = Path(directory)
        env = {**os.environ, "NOX_HOME": str(root / "nox-home")}
        version = run([NOXC, "version"], root, env)
        print((version.stdout + version.stderr).strip())
        package = root / "package"
        package.mkdir()
        manifest(package, PACKAGE_NAME, "engine.nox", [])
        (package / "clock.nox").write_text(
            "protocol Clock:\n    def now(self: Clock) -> int:\n        pass\n",
            encoding="utf-8",
        )
        (package / "engine.nox").write_text(
            f"from {PACKAGE_NAME}.clock import Clock\n\ndef read(clock: Clock) -> int:\n"
            "    return clock.now()\n",
            encoding="utf-8",
        )
        run(["git", "init", "-b", "main"], package, env)
        run(["git", "add", "."], package, env)
        run(["git", "-c", "user.name=Alias Proof", "-c", "user.email=proof@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "-m", "Package proof"], package, env)
        revision = run(["git", "rev-parse", "HEAD"], package, env).stdout.strip()

        failed = False
        for alias in (PACKAGE_NAME, "schedulelib"):
            consumer = root / alias
            consumer.mkdir()
            manifest(consumer, "alias_consumer", "main.nox", [
                {"alias": alias, "repo": str(package), "ref": revision, "require_signed_commit": False},
            ])
            (consumer / "main.nox").write_text(
                f"from {alias}.clock import Clock\nfrom {alias}.engine import read\n\n"
                "class FakeClock:\n    def now(self) -> int:\n        return 7\n\n"
                "clock: Clock = FakeClock()\nprint(read(clock))\n",
                encoding="utf-8",
            )
            run([NOXC, "fetch"], consumer, env)
            for backend in BACKENDS:
                result = run([NOXC, "run", "--backend", backend, "main.nox"], consumer, env, check=False)
                print(f"{alias} {backend}: {(result.stdout + result.stderr).strip()}")
                failed |= result.returncode != 0 or result.stdout.strip() != "7"
        return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
