# Contributing to Chronos

Chronos changes must follow [AGENTS.md](AGENTS.md) and the active release phase in [todo.md](todo.md).

## Required workflow

1. Define the smallest coherent scope and its acceptance criteria.
2. Inspect the current source, tests, and relevant Nox documentation or implementation.
3. Compile a minimal proof of concept for every uncertain Nox primitive.
4. Keep scheduling decisions separate from callback execution.
5. Add deterministic tests before relying on timing-sensitive integration tests.
6. Format, type-check, test, and run every affected example.
7. Record actual commands, results, backend coverage, and Nox issues in `NOX_LIMITATIONS.md`.
8. Update public API documentation and the changelog in the same change.

## Baseline checks

The project is in Phase 3. The portable baseline checks are:

```sh
noxc test tests
for source in tests/*_test.nox; do noxc run --backend qbe "$source"; done
noxc check --profile freestanding policy.nox
noxc check --profile freestanding scheduler.nox
```

Do not add dependencies, modify the Nox compiler/runtime/stdlib, publish a release, or expand deferred scope without explicit approval.
