# Nox limitations observed by Chronos

This file tracks compiler/runtime behavior encountered while implementing Chronos. It is intentionally separate from Chronos feature limitations. Entries remain open until the relevant Nox fix is verified with the recorded reproducer on every affected backend.

Original observations used Nox 2.1.0 on macOS arm64. The latest audit used Nox 2.1.111 on macOS arm64 on 2026-11-13. Chronos does not modify the Nox compiler, runtime, or standard library.

## NXL-001 — production-shaped optional primitive fields reach unsupported codegen

Status: open; no reliable minimal reproducer is available for a Nox 2.1.111 re-audit

Observed: 2026-11-10

Affected stage: code generation after successful type checking

A production-shaped job class containing `int | None` fields for next-run and completion timestamps passed `noxc check` but failed during code generation through the generic unsupported-codegen path. A small standalone optional-field probe succeeded, so this is not yet reduced to a reliable minimal reproducer; the failure appears to require the larger combination of subclasses, protocol-valued trigger fields, closure-valued handlers, and optional primitive fields.

Chronos workaround: store an explicit discriminator/`has_*` boolean plus a nonoptional integer field. See `Job.has_last_completion` and `ScheduledEntry.has_next`.

Fix verification:

1. Restore optional timestamp fields in an isolated copy of the production-shaped job/scheduler model.
2. Run `noxc check`, LLVM execution, and QBE execution.
3. Remove the workaround only after both backends execute the job and scheduler tests.

## NXL-002 — mutating a class-valued list parameter with `insert` reaches unsupported codegen

Status: resolved in Nox 2.1.98; Chronos workaround retained because no refactor is required

Observed: 2026-11-10

Affected stage: code generation after successful type checking

A scheduler helper accepted `list[DueItem]` as a parameter and called `items.insert(index, candidate)`. Type checking succeeded, but code generation reached the generic unsupported-codegen path. Performing the same insertion on a locally owned `list[DueItem]` inside `_collect_due` compiles and runs on LLVM and QBE.

Minimal reproducer: `proofs/limitations/list_parameter_insert.nox`.

```text
noxc check proofs/limitations/list_parameter_insert.nox        -> no type errors
noxc run proofs/limitations/list_parameter_insert.nox          -> unsupported codegen
noxc run --backend qbe proofs/limitations/list_parameter_insert.nox -> unsupported codegen
```

Chronos workaround: do not mutate class-valued list parameters in this path; build and insert into the local result list.

Fix verification:

1. Run the retained reproducer on LLVM and QBE and confirm it prints `7`.
2. Restore the helper-shaped scheduler implementation.
3. Run the full scheduler matrix before removing the workaround.

Resolution evidence (2026-11-13): the retained reproducer printed `7` on both LLVM and QBE with Nox 2.1.98. Chronos does not immediately reintroduce the helper because the local-list implementation is correct and a refactor has no current product benefit.

## NXL-003 — local names matching imported module aliases resolve as modules

Status: open

Observed: 2026-11-10

Affected stage: name resolution/type checking

With `from clock import FakeClock`, a module-level local named `clock` followed by `clock.advance(...)` was resolved as the imported `clock` module. The compiler reported that module `clock` had no member `advance` instead of resolving the annotated local variable.

Chronos workaround: use noncolliding names such as `source_clock`, `event_clock`, `target`, `store`, and `engine` rather than `clock`, `job`, `registry`, or other imported module aliases.

Reproducer: `proofs/limitations/module_alias_shadow.nox`.

```text
noxc check proofs/limitations/module_alias_shadow.nox -> UndefinedFunction: module 'clock' has no member named 'advance'/'now_utc'
noxc check --backend qbe proofs/limitations/module_alias_shadow.nox -> same errors
```

Fix verification: compile `proofs/limitations/module_alias_shadow.nox` and confirm the local binding wins consistently on LLVM and QBE, printing `1`.

Latest audit (2026-11-13, Nox 2.1.98): still open. `noxc check` reports the same `UndefinedFunction` errors for `clock.advance` and `clock.now_utc`.

Nox 2.1.111 audit: still open with the same two `UndefinedFunction` errors.

## NXL-004 — pre-epoch `DateTime.to_epoch_ms()` did not complete

Status: resolved in Nox 2.1.98; Chronos nonnegative public range remains an explicit compatibility decision

Observed: 2026-11-10

Affected stage: runtime calendar conversion

`DateTime(1969, 12, 27, ...).to_epoch_ms()` did not complete on the installed toolchain. Positive epoch/calendar round trips completed on LLVM and QBE. Chronos therefore cannot safely advertise historical negative Unix timestamps. The source is retained as `proofs/limitations/pre_epoch_datetime.nox`; run it only under an external timeout until the runtime issue is fixed.

Chronos workaround: `UtcInstant` rejects values below Unix epoch `0`. Cron search and public timestamp APIs inherit this explicit range.

Fix verification:

1. Run bounded pre-epoch round trips around 1969-12-31 and earlier leap-year boundaries.
2. Verify identical finite results on LLVM and QBE.
3. Extend Chronos timestamp range only after regression tests cover conversion and cron traversal.

Resolution evidence (2026-11-13): the retained reproducer completed on LLVM and QBE with Nox 2.1.98 and printed `-432000000`. Chronos continues to reject negative `UtcInstant` values until a separate versioned range expansion includes calendar, trigger, and cron regression coverage.

## NXL-005 — omitted default optional argument fails across a module boundary

Status: open

Observed: 2026-11-11

Affected stage: cross-module type checking

Adding a trailing `policy_config: JobPolicies | None = None` parameter to the exported `make_utc_job`, `make_monotonic_job`, and `make_fixed_delay_job` functions allowed `job.nox` itself to pass `noxc check`. Existing calls from test modules that omitted the new defaulted argument then failed with `TypeMismatch` for the generated factory argument on both the default and QBE checks.

Reproducer modules:

- `proofs/limitations/default_policy_factory.nox` — exported function; passes its own check.
- `proofs/limitations/default_policy_factory_consumer.nox` — omits the trailing default; fails.

```text
noxc check proofs/limitations/default_policy_factory.nox -> no type errors
noxc check proofs/limitations/default_policy_factory_consumer.nox -> TypeMismatch
noxc check --backend qbe proofs/limitations/default_policy_factory_consumer.nox -> TypeMismatch
```

Expected behavior: callers may omit a trailing parameter whose default is the literal `None`, as documented for Nox functions. Observed behavior: the default is not applied correctly for these exported factories, which also contain protocol-typed and closure-typed parameters.

Chronos workaround: preserve the original factory signatures and expose explicit `make_*_with_policies` factories with a required `JobPolicies` argument.

Fix verification:

1. Reduce the failure to an exported function with a protocol parameter, closure parameter, and trailing optional class default.
2. Verify an importing module can omit the argument on LLVM and QBE.
3. Consider consolidating the companion factories only after the original call form remains source-compatible.

Latest audit (2026-11-13, Nox 2.1.98): still open. The producer module passes checking, while the importing consumer still fails with `TypeMismatch` when it omits the trailing optional argument.

Nox 2.1.111 audit: still open with the same cross-module `TypeMismatch`.

## NXL-006 — task cancellation cannot interrupt non-awaiting callback work

Status: open capability limitation

Observed: 2026-11-09; reverified 2026-11-13 with Nox 2.1.111

Affected stage: hosted task runtime and shutdown/timeout design

`Task.cancel()` is cooperative. A task observes cancellation at an `await`/cancellation checkpoint, but pure computation with no such point runs to completion. `proofs/concurrency_model.nox` cancels both forms: the awaiting worker raises `CancelledError`, while the pure loop still returns `49995000` on LLVM and QBE.

Chronos impact: an inline trusted handler cannot be interrupted safely. Chronos therefore offers no immediate callback cancellation or execution-timeout guarantee. `stop()` lets the active inline callback finish and prevents every later callback from starting.

This is not treated as a correctness bug in documented cooperative cancellation. It is tracked because a future Nox isolation or hard-cancellation primitive would enable a distinct executor with enforceable timeout semantics.

Fix/capability verification:

1. Provide an explicitly isolated execution primitive whose termination does not corrupt the host runtime or shared state.
2. Demonstrate bounded termination of non-awaiting work on LLVM and QBE.
3. Keep cooperative `Task.cancel()` semantics distinct from hard isolation in Nox documentation and types.
4. Add a separate Chronos executor only after handler ownership, cleanup, and result propagation pass integration tests.

## NXL-007 — a package cannot use one internal import form in both its own project and a consumer

Status: open

Observed: 2026-11-13 with Nox 2.1.111 on macOS arm64

Affected stage: project/package module resolution

Nox packages are documented to import their own modules through the package's manifest name. For example, a Chronos module should use `from chronos.time import UtcInstant`. This works when Chronos is loaded as a dependency because the resolver reads the dependency's `nox.json.name` and strips that first segment.

The same source does not resolve when checked from the Chronos project itself. The top-level project resolver does not bind its own manifest name to its project root, so `chronos.time` is searched as `<project>/chronos/time.nox` instead of `<project>/time.nox`. The retained reproducer is `proofs/limitations/package_self_import.nox`:

```text
noxc check proofs/limitations/package_self_import.nox
-> import: unknown alias, or project file not found
```

Using an unqualified internal import such as `from time import UtcInstant` makes the source checkout compile, but it is not a safe package workaround. When the module is loaded through a dependency alias, that unqualified import is resolved against the consumer's project root. It either fails when the consumer has no matching file or can bind to unrelated consumer code.

Chronos impact: Chronos remains source-checkout-only and does not claim working `noxc add` consumption while this limitation is open. README examples use checkout-local imports. CI still verifies all implemented behavior directly on every claimed platform/backend.

Fix verification:

1. Bind the current project's own `nox.json.name` to its project root during recursive import resolution, using the same own-name rule already applied inside dependencies.
2. Convert Chronos internal imports to `chronos.*`.
3. Run the complete Chronos matrix from the repository root.
4. Fetch Chronos into a separate consumer under both the `chronos` alias and a deliberately different alias; compile and run the public cron and scheduler examples in both cases.

## New entry template

Every new limitation should record:

- a stable `NXL-###` identifier and status;
- compiler version, platform, backend, and failing stage;
- the smallest reliable reproducer or why minimization is incomplete;
- expected and observed behavior;
- the Chronos workaround and its cost;
- exact verification steps required before removing the workaround.
