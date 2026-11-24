# Chronos migration guide

Status: `0.5.0` source release.

Chronos follows Semantic Versioning, but the repository is still on an unreleased `0.x` development line. This guide is for applications pinned to an earlier Chronos commit. It does not imply that `0.1.0`, `0.2.0`, or `0.3.0` was published.

External package installation is not supported yet. Nox's open `NXL-007` self-import limitation still prevents one safe import form from working in both the Chronos project root and an external consumer. Use the checkout-local imports shown by the executable examples until a package-consumer test passes.

## Development boundaries

| Boundary | Representative commit | Manifest version | Meaning |
|---|---|---|---|
| Pure time, triggers, and UTC cron | `77513b1` | `0.1.0-dev` | Phase 1 development snapshot |
| Manual scheduler and lifecycle events | `38bd443` | `0.2.0-dev` | Phase 2 development snapshot |
| Bounded policy and shutdown work | `0568233` | `0.2.0-dev` | Phase 3 roadmap work; the manifest was not advanced to `0.3.0-dev` |
| Portability and curated API | `818c985` and `0f3380e` | `0.4.0-dev` | Public allowlist plus LLVM/QBE contract test |
| Optional SQLite persistence | `24f970d` | `0.5.0-dev` | Verified single-owner UTC delivery and schema v2 |

These commits are audit boundaries, not release tags. The authoritative current surface is always [the public API allowlist](api.md).

## Entering `0.5.0`

The opt-in `store` module provides `StoredJobDefinition` and `JobStore`. The optional SQLite adapter opens a single-owner store through `open_sqlite_store(path)`. Applications use `HandlerRegistry` to bind trusted callbacks and rebuild `PersistentScheduler` watches after startup. SQLite retains the consumed state of UTC one-shots and the current cursor of persisted UTC cron jobs.

Persisted definitions use handler keys rather than closures/function pointers and require compare-and-swap revisions. Format versions are explicit and unknown versions fail closed. See [optional persistence](persistence.md) before implementing an application adapter against this experimental contract.

Applications using the Chronos UTC codec must write the canonical trigger and policy values described in the [version 1 format reference](persistence.md#utc-definition-codec). Earlier development snapshots stored opaque application values. Those records still load from the store. Translate their configurations explicitly before passing them to `restore_utc_job`.

Opening a schema v1 SQLite file with this snapshot upgrades it to v2 in one transaction. Job records and delivery cursors keep their existing values. The new outcome table starts empty. Older Chronos binaries reject schema v2.

## Upgrade checklist for `0.4.0-dev`

1. Replace direct imports of registry, executor, dispatcher, concrete job, and scheduler-record types with names from the [public API allowlist](api.md).
2. Construct jobs with `make_utc_job`, `make_monotonic_job`, or `make_fixed_delay_job`. Use the corresponding `_with_policies` factory when behavior must differ from the defaults.
3. Own one `Scheduler`, call `start()`, drive it with bounded application calls to `tick()`, and call terminal `stop()` during shutdown.
4. Route registration, removal, enable/disable, inspection, and listeners through `Scheduler`.
5. Update custom triggers to implement both exclusive `next_fire_after` and inclusive `next_fire_at_or_after`.
6. Select an explicit bounded misfire, overlap, and retry policy when the defaults do not express the application's delivery requirements.
7. Treat `ChronosEvent` as a scheduler-produced value. Handle the documented policy event kinds and do not construct events or dispatch them through `EventDispatcher`.
8. Stop importing raw constants, mutable fields, leading-underscore helpers, or any symbol merely because Nox permits the import. Nox does not enforce the Chronos support boundary; [the allowlist](api.md) does.

## Public replacement map

| Earlier development usage | `0.4.0-dev` replacement | Migration note |
|---|---|---|
| `JobRegistry` / `RegisteredJob` | `Scheduler.add`, `remove`, `enable`, `disable`, `list_jobs` | The scheduler owns registry and scheduling invariants together. |
| `UtcJob`, `MonotonicJob`, `FixedDelayJob` constructors | `make_utc_job`, `make_monotonic_job`, `make_fixed_delay_job` | Concrete constructors gained policy state and are Internal. |
| Custom policy-bearing concrete constructors | `make_*_with_policies` | Pass a validated `JobPolicies` bundle as the final argument. |
| `InlineExecutor` / `ExecutionOutcome` | `Scheduler.tick()` and `TickResult` | There is no public executor extension point or timeout guarantee. |
| `EventDispatcher` | `Scheduler.add_listener`, `listener_count`, `listener_failure_count` | Events are synchronously produced by the scheduler; no event queue is retained. |
| `CronField.values` / `CronField.wildcard` | `CronSchedule.matches`, `next_fire_after`, `next_fire_at_or_after` | The parser representation and its mutable storage are Internal. |
| Direct `Job.run`, scheduling accessors, and outcome mutation | Scheduler operations and documented read-only job fields | Handler dispatch and completion recording belong to the scheduler/executor boundary. |
| `ScheduledEntry`, `DueItem`, raw state/kind/bound constants | Documented `Scheduler`, policy factories, event constants, and `TickResult` fields | Internal storage and raw discriminants may change without migration support. |

The existing non-policy job factories remain source-compatible. They now install `default_job_policies()`: maximum-grace fire-once misfire handling, forbidden overlap, and no retry.

## From the `0.1.0-dev` trigger snapshot

### Custom trigger protocols gained an inclusive operation

The Phase 1 protocols required only `next_fire_after(reference)`. Scheduler registration must preserve a target exactly equal to the registration clock, so Phase 2 added:

- `UtcTrigger.next_fire_at_or_after(reference)`;
- `MonotonicTrigger.next_fire_at_or_after(reference)`.

Custom structural trigger implementations must provide both methods. The exclusive method must return only a strictly later occurrence. The inclusive method may return the reference when it is an exact matching boundary. Both recurring operations must remain deterministic and increasing after the selected occurrence.

Built-in `OnceTrigger`, `DelayTrigger`, `FixedRateTrigger`, and `CronTrigger` already implement this contract.

### Scheduling became application-owned

Phase 1 trigger calculation remains pure. Do not add sleeps, tasks, or callbacks to custom triggers. Create a `Scheduler` with an injected `Clock`, register factory-created jobs, call `start()`, and invoke `tick()` from an application-owned polling boundary. Chronos still has no supported background scheduler.

## From the `0.2.0-dev` scheduler snapshot

### Use factories instead of concrete job constructors

Policy work added a validated `JobPolicies` value to internal concrete job state. Code that directly constructed `UtcJob`, `MonotonicJob`, `FixedDelayJob`, or the base `Job` no longer matches those constructor signatures and was coupled to scheduler-only methods.

Use the source-compatible factories when defaults are correct. Use `make_utc_job_with_policies`, `make_monotonic_job_with_policies`, or `make_fixed_delay_job_with_policies` for explicit policy configuration. Factory return values use the shared `Job` inspection type.

### Late runs now have explicit bounded policy semantics

The early scheduler had provisional missed-run behavior. `0.4.0-dev` evaluates lateness through a job's policy:

- `skip_misfires` discards every late occurrence;
- `fire_once_misfires` runs at most one occurrence within grace;
- `catch_up_misfires` runs at most the configured count and bounds discovery work separately;
- all modes establish one bounded next occurrence after evaluation; cron and fixed-rate schedules retain their original anchors.

The default factories use maximum-grace fire-once, so an overdue recurring schedule produces one execution rather than an unbounded drain. Applications that intentionally need more than one missed occurrence must opt into bounded catch-up. Fixed-delay jobs cannot use catch-up because their next occurrence depends on an actual completion.

Phase 4 security hardening also caps the aggregate catch-up work of one tick at 1,024 dispatch candidates and 10,000 next-occurrence evaluations across all jobs. Earlier snapshots applied those bounds independently per job. Applications with several large backlogs must continue application-driven polling; jobs reached after the global budget is exhausted remain due for a later tick.

Overlap defaults to `forbid_overlap()` and retry defaults to `no_retry()`. `queue_one_overlap()` retains at most one same-thread reentrant occurrence. Fixed and exponential retry use monotonic deadlines and bounded total attempts. Catch-up/retry and queue-one/retry combinations remain rejected.

### Shutdown is terminal

`stop()` is idempotent but terminal. A stopped scheduler cannot restart. A stop requested from the active inline callback drains only that callback and prevents later snapshot, retry, or queued-overlap work from starting. There is no force-cancel, background join, or handler timeout API.

### Result and event construction is no longer public

`TickResult` gained bounded policy counters, while `ChronosEvent` gained policy event kinds and coalescing fields. Read documented fields on scheduler-produced values, but do not instantiate `TickResult`, `ChronosEvent`, `EventDispatcher`, `ScheduledEntry`, or `DueItem` directly.

Listeners that branch on event kind should recognize `misfired`, `skipped`, `coalesced`, `overlap-queued`, `overlap-skipped`, and `retried` in addition to the original lifecycle kinds. Unknown future Experimental kinds should be ignored safely unless the application deliberately treats them as fatal.

## The `0.4.0-dev` support boundary

Before `818c985`, documentation exposed implementation types that were importable but unsuitable as extension points. The curated allowlist now classifies every listed name as Experimental and every unlisted name as Internal. There are no Stable or Deprecated names before the first tagged release and a passing external-consumer test.

This classification is a compatibility break for source checkouts that imported implementation details, even though Nox still allows those imports. Internal names receive no deprecation window during `0.x` development. Public Experimental changes must be recorded in this guide and [the changelog](../CHANGELOG.md) and covered by the API contract test.

## Verification after migration

Run the repository matrix with the checksum-pinned core compiler:

```sh
python3 scripts/verify.py
```

This executes the aggregate suite, every test and example on LLVM/QBE, runtime proofs, freestanding checks, and benchmark type-checks. Optional Nyx/Aether examples have their separate Nox 2.1.186 verifier documented in [framework integrations](integrations.md).

The SQLite primitive check is also isolated from the dependency-free core matrix:

```sh
python3 scripts/verify_persistence.py
```

The verification covers SQLite primitives and definition storage. Scheduler restart behavior requires separate verification. See [optional persistence](persistence.md).

Because package consumption remains blocked, a successful source-checkout matrix does not prove that `noxc add chronos` works. Do not publish that installation claim until [`NXL-007`](../NOX_LIMITATIONS.md#nxl-007--a-package-cannot-use-one-internal-import-form-in-both-its-own-project-and-a-consumer) is resolved and the dedicated consumer gate passes.
