# Contributing to Chronos

Chronos changes must follow [AGENTS.md](AGENTS.md) and the active release phase in [todo.md](todo.md).

## Required workflow

1. Define the smallest coherent scope and its acceptance criteria.
2. Inspect the current source, tests, and relevant Nox documentation or implementation.
3. Compile a minimal proof of concept for every uncertain Nox primitive.
4. Keep scheduling decisions separate from callback execution.
5. Add deterministic tests before relying on timing-sensitive integration tests.
6. Format, type-check, test, and run every affected example.
7. Record actual commands, results, backend coverage, and limitations.
8. Update public API documentation and the changelog in the same change.

## Baseline checks

The project is still in Phase 0. The current baseline checks are:

```sh
noxc check examples/calendar_probe.nox
noxc check --profile freestanding examples/calendar_probe.nox
noxc test tests
noxc run --backend llvm examples/calendar_probe.nox
noxc run --backend qbe examples/calendar_probe.nox
```

Do not add dependencies, modify the Nox compiler/runtime/stdlib, publish a release, or expand deferred scope without explicit approval.
