# Contributing to Chronos

Thank you for helping improve Chronos. Correct time semantics and verifiable Nox behavior take priority over API breadth.

## Before opening a change

1. Read the binding engineering rules in [AGENTS.md](AGENTS.md).
2. Check the active release phase and acceptance criteria in [todo.md](todo.md).
3. Search existing issues and discussions before starting overlapping work.
4. Open an issue first for public API changes, new dependencies, concurrency, persistence, time zones, or distributed behavior.

Do not modify the Nox compiler, runtime, or standard library as part of a Chronos change. Compiler/runtime findings belong in [NOX_LIMITATIONS.md](NOX_LIMITATIONS.md) with a minimal reproducer where possible.

## Development setup

Chronos currently verifies against Nox 2.1.111. Install Nox from the [official download page](https://noxlang.com/download/), then clone the repository:

```sh
git clone https://github.com/mburakmmm/chronos.git
cd chronos
noxc version
```

The repository has no mandatory third-party package dependency.

## Required engineering workflow

1. Define the smallest coherent scope and its acceptance criteria.
2. Inspect current source, tests, and relevant Nox documentation or implementation.
3. Compile a focused proof for every uncertain callback, task, channel, cancellation, clock, or type behavior.
4. Keep trigger calculation separate from execution, sleeping, I/O, and global state.
5. Add deterministic fake-clock tests; reserve real timing for bounded integration proofs.
6. Bound all retries, catch-up work, overlap state, listeners, history, and retained errors.
7. Update public API documentation, compatibility evidence, and the changelog with the code.
8. Add a regression test for every bug fix.

## Verification

Run the same complete matrix used by CI:

```sh
python3 scripts/verify.py
git diff --check
```

The verifier checks:

- the aggregate Nox test suite;
- all 18 test programs on LLVM and QBE;
- all 16 executable examples on LLVM and QBE;
- task sleep, channels, and cancellation proofs on both backends;
- clock-independent modules under the freestanding profile;
- the hosted `SystemClock` adapter.

When changing Nox source, run `noxc fmt` on every affected `.nox` file before the verifier.

## Pull requests

Keep pull requests focused. The description should include:

- the user-visible behavior and time semantics;
- exact commands executed and their results;
- affected backends/platforms;
- resource, shutdown, retry, overlap, and secret-handling impact;
- documentation and migration impact;
- any new or resolved Nox limitation.

Do not weaken, skip, or delete tests merely to make CI green. Do not claim a platform or feature that was not executed.

## Commit and release policy

Use concise imperative commit subjects. Chronos follows Semantic Versioning, including documented breaking changes during `0.x`.

Maintainers create tags, publish package metadata, and prepare releases. A pull request must not publish, tag, or add release credentials.

## Community

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Usage questions belong in GitHub Discussions; reproducible defects belong in GitHub Issues. See [SUPPORT.md](SUPPORT.md).
