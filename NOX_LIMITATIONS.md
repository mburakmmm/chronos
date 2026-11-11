# Nox limitations observed by Chronos

This file tracks compiler/runtime behavior encountered while implementing Chronos. It is intentionally separate from Chronos feature limitations. Entries remain open until the relevant Nox fix is verified with the recorded reproducer on every affected backend.

Environment for current observations: Nox 2.1.0, macOS arm64. Chronos does not modify the Nox compiler, runtime, or standard library.

## NXL-001 — production-shaped optional primitive fields reach unsupported codegen

Status: open

Observed: 2026-11-10

Affected stage: code generation after successful type checking

A production-shaped job class containing `int | None` fields for next-run and completion timestamps passed `noxc check` but failed during code generation through the generic unsupported-codegen path. A small standalone optional-field probe succeeded, so this is not yet reduced to a reliable minimal reproducer; the failure appears to require the larger combination of subclasses, protocol-valued trigger fields, closure-valued handlers, and optional primitive fields.

Chronos workaround: store an explicit discriminator/`has_*` boolean plus a nonoptional integer field. See `Job.has_last_completion` and `ScheduledEntry.has_next`.

Fix verification:

1. Restore optional timestamp fields in an isolated copy of the production-shaped job/scheduler model.
2. Run `noxc check`, LLVM execution, and QBE execution.
3. Remove the workaround only after both backends execute the job and scheduler tests.

## NXL-002 — mutating a class-valued list parameter with `insert` reaches unsupported codegen

Status: open

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

## NXL-004 — pre-epoch `DateTime.to_epoch_ms()` did not complete

Status: open

Observed: 2026-11-10

Affected stage: runtime calendar conversion

`DateTime(1969, 12, 27, ...).to_epoch_ms()` did not complete on the installed toolchain. Positive epoch/calendar round trips completed on LLVM and QBE. Chronos therefore cannot safely advertise historical negative Unix timestamps. The source is retained as `proofs/limitations/pre_epoch_datetime.nox`; run it only under an external timeout until the runtime issue is fixed.

Chronos workaround: `UtcInstant` rejects values below Unix epoch `0`. Cron search and public timestamp APIs inherit this explicit range.

Fix verification:

1. Run bounded pre-epoch round trips around 1969-12-31 and earlier leap-year boundaries.
2. Verify identical finite results on LLVM and QBE.
3. Extend Chronos timestamp range only after regression tests cover conversion and cron traversal.

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

## New entry template

Every new limitation should record:

- a stable `NXL-###` identifier and status;
- compiler version, platform, backend, and failing stage;
- the smallest reliable reproducer or why minimization is incomplete;
- expected and observed behavior;
- the Chronos workaround and its cost;
- exact verification steps required before removing the workaround.
