# Nox limitations observed by Chronos

This file tracks compiler/runtime behavior encountered while implementing Chronos. It is intentionally separate from Chronos feature limitations. Entries remain open until the relevant Nox fix is verified with the recorded reproducer on every affected backend.

Original observations used Nox 2.1.0 on macOS arm64. Historical audits used 2.1.111, 2.1.186 and 2.2.70. Chronos CI remains pinned to Nox 2.2.70.

## Nox 2.2.107 audit — 2026-11-28

The installed compiler reported `noxc 2.2.107`, matching the [latest official release at audit time](https://github.com/mburakmmm/nox-lang/releases/tag/v2.2.107). The results below are from macOS arm64 with LLVM and QBE.

| Entry | Reproduction on 2.2.107 |
|---|---|
| NXL-001 | Representative optional timestamp fields, typed trigger and captured handler work on both backends. The original larger failure has no exact reproducer. |
| NXL-002 | List-parameter insertion prints `7` on both backends. |
| NXL-003 | Original unqualified reproduction at Chronos `f78c252` and current qualified proof both print `1` on both backends. |
| NXL-004 | The pre-epoch sample prints `-432000000` on both backends. |
| NXL-005 | The importing consumer omits the optional argument on both backends. |
| NXL-006 | Cooperative cancellation works at an await or explicit `nox.tasks.checkpoint()`. Work with neither still completes on both backends. This is documented runtime behavior. |
| NXL-007 | **Open compiler bug.** Root self-import and canonical dependency imports work. A renamed dependency alias produces `DuplicateDefinition: protocol already defined: Clock` on both backends. |
| NXL-008 | A module with `__all__` rejects private imports on both backends. The legacy proof without an export list still permits them. |
| NXL-009 | SQLite returns three bytes with the NUL preserved at index 1 on both backends. |
| NXL-010 | A closure captures and mutates the list parameter on both backends. |

NXL-007 is the current upstream fix candidate. Run the standalone reproducer with `python3 scripts/reproduce_package_alias.py`. The fixture needs only Git and Nox. NXL-006 would call for a separately designed isolation feature only if forced termination is required. NXL-001 should stay provisional until an exact failing program can be recovered.

## Nox 2.2.70 audit

The following results are from macOS arm64. The 2.1.111 baseline was reproduced from the previous Chronos checkout for NXL-003, NXL-005, NXL-007 and NXL-010. For the remaining historical results, see the individual entries.

| Entry | 2.2.70 result |
|---|---|
| NXL-001 | Representative subclass, optional integer fields, typed trigger and captured handler pass on LLVM/QBE. The original failure was never reduced exactly. |
| NXL-002 | Retained list insertion proof passes on LLVM/QBE. |
| NXL-003 | Module shadowing proof with qualified imports passes on LLVM/QBE. |
| NXL-004 | Retained pre-epoch conversion returns `-432000000` on LLVM/QBE. Chronos's public epoch range remains unchanged. |
| NXL-005 | Existing importing consumer omits the default successfully on LLVM/QBE. |
| NXL-006 | Awaiting work cancels; non-awaiting work still completes. Cooperative cancellation remains a runtime contract. |
| NXL-007 | Self-import and a fetched canonical `chronos` dependency pass. A renamed `schedulelib` consumer exposes a duplicate `Clock` protocol on LLVM. |
| NXL-008 | Opt-in `__all__` rejects a private import from `handler_registry`. Legacy modules with no export list keep their original behavior. |
| NXL-009 | SQLite returns all three bytes and preserves NUL on LLVM/QBE. Chronos retains its own data-format validation. |
| NXL-010 | Retained captured-list proof passes on LLVM/QBE. |

The upstream [Nox 2.2.70 source and changelog](https://github.com/mburakmmm/nox-lang/tree/v2.2.70) contain the preceding releases. In particular, 2.2.5 introduced `__all__`. Version 2.2.63 fixed SQLite text NUL preservation and added wake-up on cancellation for blocked waits. That wake-up change is distinct from interrupting non-awaiting code.

## NXL-001 — production-shaped optional primitive fields reach unsupported codegen

Status: representative `optional_job_fields.nox` proof passes on 2.2.70 and 2.2.107 LLVM/QBE. The original failure lacked a reliable reproducer.

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

Status: original and qualified-import regression proofs pass on 2.2.70 and 2.2.107 LLVM/QBE.

Observed: 2026-11-10

Affected stage: name resolution/type checking

With `from clock import FakeClock`, a module-level local named `clock` followed by `clock.advance(...)` was resolved as the imported `clock` module. The compiler reported that module `clock` had no member `advance` instead of resolving the annotated local variable.

Chronos workaround: use noncolliding names such as `source_clock`, `event_clock`, `target`, `store`, and `engine` rather than `clock`, `job`, `registry`, or other imported module aliases.

Reproducer in the historical checkout: `proofs/limitations/module_alias_shadow.nox`. The current proof uses qualified imports consistently with the rest of the package. Mixing the old unqualified imports with today's qualified modules can produce a separate type mismatch.

```text
noxc check proofs/limitations/module_alias_shadow.nox -> UndefinedFunction: module 'clock' has no member named 'advance'/'now_utc'
noxc check --backend qbe proofs/limitations/module_alias_shadow.nox -> same errors
```

Nox 2.2.70 prints `1` on LLVM and QBE both for the original reproduction in the `f78c252` checkout and for the qualified-import regression in the current checkout.

Historical audit (2026-11-13, Nox 2.1.98): `noxc check` reported the same `UndefinedFunction` errors for `clock.advance` and `clock.now_utc`.

Nox 2.1.111 audit: still open with the same two `UndefinedFunction` errors.

Phase 6 reproduced the collision with a local `trigger: LocalCronPrototype` and a transitively imported `trigger` module. A call to `trigger.next_fire_at_or_after` was resolved as a module member. Renaming the local to `local_schedule` fixed the type check.

Nox 2.1.186 integration audit: still open. A flat Chronos/Nyx source overlay resolved Nyx locals named `errors` and `registry` as the Chronos module aliases, producing `module 'errors' has no member named 'append'` and `module 'registry' has no member named 'has'`. Moving Chronos under the qualified `chronos.*` namespace avoids these cross-library collisions without renaming framework locals.

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

Status: retained importing consumer passes on 2.2.70 and 2.2.107 LLVM/QBE.

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

Historical audit (2026-11-13, Nox 2.1.98): the producer passed checking, while the importing consumer failed with `TypeMismatch` when it omitted the trailing optional argument.

Nox 2.1.111 audit: still open with the same cross-module `TypeMismatch`.

## NXL-006 — task cancellation cannot interrupt non-awaiting callback work

Status: documented cooperative capability on 2.2.107. No hard cancellation contract.

Observed: 2026-11-09; reverified 2026-11-13 with Nox 2.1.111

Affected stage: hosted task runtime and shutdown/timeout design

`Task.cancel()` is cooperative. On 2.2.107 the awaiting worker in `proofs/concurrency_model.nox` raises `CancelledError`, while the pure loop still returns `49995000` on both backends. The separate `proofs/limitations/cooperative_checkpoint.nox` proof prints `cancelled at checkpoint` on both. The checkpoint API was introduced in 2.1.19. Nox 2.2.63 added wake-up for suspended receive and task-await paths. See [the 2.2.107 cancellation contract](https://github.com/mburakmmm/nox-lang/blob/v2.2.107/docs/language/concurrency.md#cancellation).

Chronos impact: an inline trusted handler cannot be interrupted safely. Chronos therefore offers no immediate callback cancellation or execution-timeout guarantee. `stop()` lets the active inline callback finish and prevents every later callback from starting.

This is not treated as a correctness bug in documented cooperative cancellation. It is tracked because a future Nox isolation or hard-cancellation primitive would enable a distinct executor with enforceable timeout semantics.

Fix/capability verification:

1. Provide an explicitly isolated execution primitive whose termination does not corrupt the host runtime or shared state.
2. Demonstrate bounded termination of non-awaiting work on LLVM and QBE.
3. Keep cooperative `Task.cancel()` semantics distinct from hard isolation in Nox documentation and types.
4. Add a separate Chronos executor only after handler ownership, cleanup, and result propagation pass integration tests.

## NXL-007 — a package cannot use one internal import form in both its own project and a consumer

Status: project self-import and canonical alias work. Renamed dependency aliases still fail with duplicate module definitions on Nox 2.2.107 LLVM/QBE.

Observed: 2026-11-13 with Nox 2.1.111 on macOS arm64

Affected stage: project/package module resolution

Nox packages are documented to import their own modules through the package's manifest name. For example, a Chronos module should use `from chronos.time import UtcInstant`. This works when Chronos is loaded as a dependency because the resolver reads the dependency's `nox.json.name` and strips that first segment.

On Nox 2.1.111 the same source did not resolve when checked from the Chronos project itself. The top-level resolver searched `<project>/chronos/time.nox` instead of `<project>/time.nox`. The retained reproducer is `proofs/limitations/package_self_import.nox`:

```text
noxc check proofs/limitations/package_self_import.nox
-> import: unknown alias, or project file not found
```

Using an unqualified internal import such as `from time import UtcInstant` makes the source checkout compile, but it is not a safe package workaround. When the module is loaded through a dependency alias, that unqualified import is resolved against the consumer's project root. It either fails when the consumer has no matching file or can bind to unrelated consumer code.

Previous Chronos impact: the v0.5.0 release is source-checkout-only. The current development line uses package-qualified imports and verifies Git dependency consumption under `chronos`.

The installed 2.2.87 compiler also passed the canonical cron and scheduler consumers on LLVM/QBE. The alternate `schedulelib` alias again produced `DuplicateDefinition: protocol already defined: Clock` on LLVM.

The 2.2.107 audit reproduced the error with the full Chronos scheduler consumer and with [a two-module fixture](scripts/reproduce_package_alias.py). In the minimal case `engine.nox` imports `Clock` through the package's own name, and the consumer imports `Clock` and the engine through its chosen alias. The canonical alias prints `7`. A renamed alias reports a duplicate protocol at line 1 on both backends. A fix should make both names resolve to the same module identity and produce `7` for each alias/backend combination.

Nox 2.1.186 audit (2026-11-16): still open. `noxc check proofs/limitations/package_self_import.nox` reports the same unknown-alias/project-file error on LLVM and QBE checks. Optional framework verification therefore uses a documented temporary `chronos.*` source overlay and is not counted as package-consumer evidence.

Fix verification:

1. Bind the current project's own `nox.json.name` to its project root during recursive import resolution, using the same own-name rule already applied inside dependencies.
2. Convert Chronos internal imports to `chronos.*`.
3. Run the complete Chronos matrix from the repository root.
4. Fetch Chronos into a separate consumer under both the `chronos` alias and a deliberately different alias; compile and run the public cron and scheduler examples in both cases.

## NXL-008 — module visibility cannot enforce a public API allowlist

Status: opt-in `__all__` verified in `handler_registry` on 2.2.70 and 2.2.107 LLVM/QBE.

Observed: 2026-11-16 with Nox 2.1.111 and 2.1.186 on macOS arm64

Affected stage: language/module API design

In the 2.1.x baseline, all top-level module names were importable and a leading underscore was only a convention.

The retained producer/consumer proof imports a leading-underscore class and function from another module and prints `7` then `9` on LLVM and QBE:

- `proofs/limitations/module_visibility_source.nox`
- `proofs/limitations/module_visibility_consumer.nox`

Chronos uses `__all__` in `handler_registry` to enforce its export list. Modules without an export list keep the legacy behavior, and the documented allowlist defines their supported surface.

Chronos workaround: `docs/api.md` is the authoritative allowlist, leading underscores mark helper functions, and the API documentation explicitly labels Experimental and Internal names. Tests and benchmarks may import Internal names only when their purpose requires implementation-level verification; doing so does not promote those names to public API.

Nox introduced `__all__` in 2.2.5 and extended the feature in 2.2.63. The historical visibility limitation is resolved for modules that declare an export list.

Fix/capability verification:

1. Add a documented module export allowlist or access-control mechanism with a clear migration path.
2. Confirm the retained consumer is rejected when it imports both Internal names.
3. Apply the mechanism to Chronos modules and verify the supported imports on LLVM and QBE.
4. Keep reflection, diagnostics, and package consumers consistent with the same visibility rule.

## NXL-009 — SQLite text reads truncate at embedded NUL

Status: fixed upstream in 2.2.63 and verified on 2.2.70 and 2.2.107 LLVM/QBE.

The retained `proofs/persistence/sqlite_transaction_probe.nox` queries `CAST(X'610062' AS TEXT)` and the length of the same three-byte blob. Before the fix, the runtime shim copied only the NUL-terminated span, so `Row.get_str(0)` returned `a`. The updated proof prints `3 0 3` for the Nox byte length, byte at index 1 and SQLite blob length.

Chronos rejects NUL on writes and checks text type, byte length and embedded NUL in the SQLite projection before transferring rows to Nox. The workaround adds SQL checks for each text field.

To verify a runtime fix, check that the driver returns all three bytes on both backends, or reports a documented explicit error for unsupported text. Keep Chronos's corruption regression, since embedded NUL remains outside its store format.

## NXL-010 — closures capturing a list parameter fail during code generation

Status: retained reproducer passes on 2.2.70 and 2.2.107 LLVM/QBE.

`proofs/limitations/list_parameter_closure.nox` returns a closure that captures and appends to a `list[str]` parameter. On the original baseline, `noxc check` passed but both code generators rejected the program with the generic unsupported-construct diagnostic.

Chronos uses a class instance to hold captured test state. Verify a fix by running the retained reproducer on both backends and checking that it prints `recorded`.

## New entry template

Every new limitation should record:

- a stable `NXL-###` identifier and status;
- compiler version, platform, backend, and failing stage;
- the smallest reliable reproducer or why minimization is incomplete;
- expected and observed behavior;
- the Chronos workaround and its cost;
- exact verification steps required before removing the workaround.
