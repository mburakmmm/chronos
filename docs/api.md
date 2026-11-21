# Chronos public API

Status: curated experimental surface (`0.5.0` development).

This document is the only authoritative Chronos API allowlist. Nox 2.1.111 has no module export allowlist or `public`/`private` keywords: every top-level name is technically importable, including names beginning with `_`. Importability therefore does not imply support. See `NXL-008` in `NOX_LIMITATIONS.md`. Applications pinned to an earlier development commit should follow the [migration guide](migration-guide.md).

## Stability labels

- **Stable:** compatibility is preserved according to SemVer. Chronos has no Stable names before its first tagged release and external package-consumption test.
- **Experimental:** supported and tested for the current `0.x` development line, but may change with an explicitly documented `0.x` migration.
- **Deprecated:** still supported temporarily, with a documented replacement and removal target. There are no Deprecated names today.
- **Internal:** implementation detail with no compatibility promise. This includes every name not explicitly listed as Experimental below, every leading-underscore name, mutable implementation storage, and everything under `proofs/` and `benchmarks/`.

Methods and fields are supported only when their contract is explicitly described in this document. Constructors for factory-created/result/event types are Internal unless the constructor is explicitly documented.

## Supported surface

| Module | Experimental names |
|---|---|
| `errors` | `ChronosError`, `InvalidDurationError`, `TimeRangeError`, `CronParseError`, `CronSearchLimitError`, `InvalidJobError`, `DuplicateJobError`, `JobNotFoundError`, `SchedulerStateError`, `InvalidEventError`, `EventListenerLimitError`, `InvalidPolicyError`, `StoreError`, `InvalidStoredJobError`, `StoreConflictError`, `StoreCorruptionError`, `UnsupportedStoreVersionError` |
| `time` | `MIN_MS`, `MAX_MS`, `UtcInstant`, `MonotonicInstant`, `Duration`, `add_duration`, `subtract_duration`, `add_monotonic_duration`, `elapsed_between`, `multiply_duration`, `require_positive_interval` |
| `clock` | `Clock`, `FakeClock` |
| `system_clock` | `SystemClock` |
| `trigger` | `UtcTrigger`, `MonotonicTrigger`, `OnceTrigger`, `DelayTrigger`, `FixedRateTrigger`, `FixedDelay` |
| `cron` | `CronSchedule`, `CronTrigger`, `parse` |
| `job` | `Job`, `JobContext`, `JobMetadata`, `make_utc_job`, `make_utc_job_with_policies`, `make_monotonic_job`, `make_monotonic_job_with_policies`, `make_fixed_delay_job`, `make_fixed_delay_job_with_policies` |
| `policy` | `JobPolicies`, `MisfirePolicy`, `OverlapPolicy`, `RetryPolicy`, `skip_misfires`, `fire_once_misfires`, `catch_up_misfires`, `forbid_overlap`, `queue_one_overlap`, `no_retry`, `fixed_retry`, `exponential_retry`, `default_job_policies` |
| `events` | `ChronosEvent` and the documented `EVENT_*` constants |
| `scheduler` | `Scheduler`, `TickResult` |
| `store` | `JobStore`, `StoredJobDefinition`, `make_stored_job_definition` |
| `sqlite_store` | `SQLiteJobStore`, `open_sqlite_store` |

The following previously tempting entry points are explicitly **Internal**: `InvalidTriggerError`; `CronField`; `UtcJob`, `MonotonicJob`, and `FixedDelayJob`; `RegisteredJob` and `JobRegistry`; `ExecutionOutcome` and `InlineExecutor`; `EventDispatcher`; `ScheduledEntry` and `DueItem`; raw scheduler/policy/event state, kind, and bound constants; `copy_job_policies`; and every leading-underscore helper. Applications should use factories and `Scheduler` forwarding methods instead.

Persistence schema/format constants, `copy_stored_job_definition`, the direct `StoredJobDefinition` constructor, and `UnknownHandlerError` remain Internal until the SQLite adapter and hydration contract are complete.

## `chronos.errors` — Experimental

### `ChronosError`

Base class for Chronos-specific errors.

### `InvalidDurationError`

Raised when a duration or duration multiplier violates a nonnegative/positive duration contract.

### `TimeRangeError`

Raised before a timestamp or duration operation would overflow, underflow, reverse a monotonic interval, or construct an invalid monotonic value.

Callers should branch on the exception class, not message text.

### Cron errors

- `CronParseError`: invalid cron syntax; `field_name` and bounded printable `token` identify the rejected input. The default exception message omits the user-controlled token; control-character and non-ASCII failures use an empty token. Explicitly accessed tokens remain untrusted data.
- `CronSearchLimitError`: a valid expression produced no match within the bounded search horizon or transition limit.

### Job errors

- `InvalidJobError`: invalid job configuration, bounded resource violation, or registry invariant failure.
- `DuplicateJobError`: an ID is already present; `job_id` contains the rejected ID.
- `JobNotFoundError`: an operation targeted an absent ID; `job_id` contains that ID.
- `SchedulerStateError`: an operation is invalid for the scheduler lifecycle; `state` contains the observed state.
- `InvalidEventError`: an event or listener-capacity configuration violates the event contract.
- `EventListenerLimitError`: listener registration exceeded the scheduler's configured capacity; `limit` contains that capacity.
- `InvalidPolicyError`: a policy kind, bound, attempt, delay, or occurrence count violates the finite policy contract.

### Store errors

- `StoreError`: base class for optional persistence boundary failures.
- `InvalidStoredJobError`: a stored definition violates identity, size, timestamp, or revision bounds.
- `StoreConflictError`: a compare-and-swap create/update/delete observed a missing, duplicate, stale, or skipped revision. Its `job_id`, `expected_revision`, and `actual_revision` fields describe the conflict without exposing stored configuration.
- `StoreCorruptionError`: an adapter found invalid persisted state. Its message is fixed and safe; `category` identifies an adapter-defined safe reason without reflecting raw rows.
- `UnsupportedStoreVersionError`: persisted `component` has `found_version` rather than `supported_version`.

## `chronos.time` — Experimental

### `UtcInstant(epoch_ms)`

A Unix epoch millisecond value from `0` through signed `int64` maximum. Negative/pre-1970 values raise `TimeRangeError`. `as_epoch_ms()` returns the raw value.

### `MonotonicInstant(value_ms)`

A nonnegative monotonic counter value. It has no UTC meaning and cannot be converted to calendar time. `as_ms()` returns the counter value.

### `Duration(value_ms)`

A nonnegative elapsed duration in milliseconds. Negative input raises `InvalidDurationError`. `as_ms()` returns the raw duration.

### Arithmetic

- `add_duration(instant, duration) -> UtcInstant`
- `subtract_duration(instant, duration) -> UtcInstant`
- `add_monotonic_duration(instant, duration) -> MonotonicInstant`
- `elapsed_between(start, end) -> Duration`
- `multiply_duration(duration, factor) -> Duration`
- `require_positive_interval(duration) -> Duration`

All operations reject invalid input or overflow before Nox's wrapping integer arithmetic can occur.

`MIN_MS` (`0`) and `MAX_MS` expose the supported UTC/duration millisecond bounds.

## `chronos.clock` — Experimental

### `Clock`

A structural protocol with:

- `now_utc() -> UtcInstant`
- `now_monotonic() -> MonotonicInstant`

### `FakeClock(utc_ms, monotonic_ms)`

A deterministic clock for tests and externally driven simulations.

- `advance(duration)` advances UTC and monotonic values atomically.
- `jump_utc_ms(delta_ms)` simulates a wall-clock correction without changing monotonic time.
- `set_utc_ms(utc_ms)` sets wall time without changing monotonic time.

Failed `advance` operations leave both values unchanged.

`chronos.clock` is pure and type-checks in Nox's freestanding profile.

## `chronos.system_clock` — Experimental

### `SystemClock`

Production `Clock` implementation:

- UTC comes from `nox.time.now_ms()`.
- monotonic elapsed time comes from suspend-inclusive `nox.time.boot_ms()`.

This module requires Nox's hosted `clock` capability and is unavailable in the freestanding profile.

## `chronos.trigger` — Experimental

Calendar and elapsed-time triggers use distinct protocols so UTC and monotonic values cannot be mixed.

### `UtcTrigger`

Structural protocol with strictly-exclusive `next_fire_after(reference)` and inclusive `next_fire_at_or_after(reference)` operations.

### `MonotonicTrigger`

Structural protocol with the same exclusive/inclusive pair for `MonotonicInstant`.

Schedulers use the inclusive operation only to preserve an occurrence exactly at registration/enable time. Recurrence uses the exclusive operation so every next result advances.

### `OnceTrigger(target)`

Returns its UTC target only when the target is strictly after the reference, otherwise `None`.

### `DelayTrigger(registered_at, delay)`

Calculates one monotonic deadline from registration time plus a nonnegative duration. It returns that deadline only while it remains strictly after the reference.

### `FixedRateTrigger(anchor, interval)`

Produces monotonic occurrences anchored to the original start. The interval must be greater than zero. The next occurrence is calculated mathematically without repeated addition, so callback duration and long gaps do not shift the anchor.

### `FixedDelay(delay)`

Stores a positive fixed-delay configuration. `next_after_completion(completed_at)` returns completion plus delay. Scheduler state owns the completion timestamp; fixed-delay is not treated as fixed-rate recurrence.

## `chronos.cron` — Experimental

### `parse(expression) -> CronSchedule`

Parses the bounded five-field UTC dialect documented in `docs/cron.md`. Malformed input raises `CronParseError`, which records the field name and bounded offending token.

### `CronSchedule.next_fire_after(reference) -> UtcInstant`

Returns the first UTC minute boundary strictly after `reference`. The algorithm jumps calendar fields and days rather than scanning every minute.

If a syntactically valid expression has no match within eight calendar years or 100,000 transitions, it raises `CronSearchLimitError`. Timestamp overflow raises `TimeRangeError` and is distinct from both parse and search errors.

Parsing normalizes allowed values to sorted unique values. Whether a field was written exactly as `*` remains significant for DOM/DOW semantics. The `CronField` representation and its mutable storage are Internal.

`next_fire_at_or_after(reference)` preserves a matching exact minute boundary. `matches(candidate)` reports whether a minute-aligned UTC instant matches the schedule.

### `CronTrigger(schedule)`

Adapts an already parsed `CronSchedule` to the optional-return `UtcTrigger` protocol without parsing the expression again. Search-limit and time-range failures remain explicit exceptions.

## `chronos.job` — Experimental

### Job construction

- `make_utc_job(job_id, name, trigger, handler, enabled, created_at, metadata) -> Job`
- `make_monotonic_job(job_id, name, trigger, handler, enabled, created_at, metadata) -> Job`
- `make_fixed_delay_job(job_id, name, schedule, registered_at, handler, enabled, created_at, metadata) -> Job`
- `make_utc_job_with_policies(..., policy_config) -> Job`
- `make_monotonic_job_with_policies(..., policy_config) -> Job`
- `make_fixed_delay_job_with_policies(..., policy_config) -> Job`

The factories create the supported UTC or monotonic job subtype. Original factories install default policies; `_with_policies` variants require `JobPolicies`. `Job.policy_config()` returns a defensive copy. `Job` is the shared consumer inspection view; direct construction of `Job` or its concrete subtypes is Internal.

`job_id` is 1–128 ASCII bytes using letters, digits, `.`, `-`, `_`, or `:`. Names are 1–256 UTF-8 bytes. Each job owns a defensive copy of at most 16 `JobMetadata` entries; keys are bounded identifiers and values are at most 256 bytes.

Handlers have the verified type `(JobContext) -> None`. A context carries `job_id`, an explicit `time_domain` (`utc` or `monotonic`), `scheduled_time_ms`, and a positive attempt number. The domain must be checked before interpreting the millisecond value.

Chronos retains only the latest fixed status, bounded safe error category, completion timestamp, and total execution count. Arbitrary results, exception messages, and history are not retained. Direct `run`, `set_enabled`, `record_success`, and `record_failure` calls are Internal scheduler/executor operations.

### Trigger access — Internal

- `trigger_kind() -> str`
- `time_domain() -> str`
- `next_utc_after(reference) -> UtcInstant | None`
- `next_utc_at_or_after(reference) -> UtcInstant | None`
- `next_monotonic_after(reference) -> MonotonicInstant | None`
- `next_monotonic_at_or_after(reference) -> MonotonicInstant | None`
- `next_monotonic_after_completion(completed_at) -> MonotonicInstant`

Calling the wrong-domain method raises `InvalidJobError`.

`make_fixed_delay_job` stores a `FixedDelay` configuration and calculates its first monotonic deadline from `registered_at`. Only fixed-delay jobs support `next_monotonic_after_completion`; the manual scheduler calls it after both successful and failed handlers.

## `chronos.store` — Experimental contract only

`StoredJobDefinition` is a bounded serializable definition containing a job ID/name, handler key and opaque handler configuration, trigger kind/configuration, policy configuration, enabled state, UTC creation/update times, compare-and-swap revision, and explicit format versions. It never contains a callback, closure, function pointer, live connection, or running scheduler state.

`make_stored_job_definition(...)` fills the currently supported format versions and validates all bounds. Handler configuration may be empty; trigger and policy configuration may not. Each configuration string is limited to 16,384 bytes and rejects embedded NUL. The values are untrusted data and are not interpreted by this contract.

`JobStore` is a structural protocol with `load`, `load_all`, `put`, `delete`, and `close`. `put(definition, 0)` means create revision `1`; updates require the stored revision to equal `expected_revision` and the replacement revision to be exactly one greater. Delete also requires an exact revision. Implementations return defensive definitions.

The optional `sqlite_store` module implements this contract for one application-owned SQLite connection. `open_sqlite_store(path)` creates or validates schema version `1`; `SQLiteJobStore` provides the protocol operations and idempotent `close()`. The adapter is single-process/single-owner, uses prepared bindings and atomic revision-checked SQL statements, validates rows on load, and redacts raw database diagnostics. It stores definitions only.

`Scheduler` does not accept a store, hydrate a handler, or restore execution state. Importing or opening the adapter therefore does not provide durable scheduling, restart delivery, migration support, worker coordination, or exactly-once behavior. See [optional persistence](persistence.md).

## `chronos.registry` — Internal

`JobRegistry` and `RegisteredJob` are scheduler implementation details. Applications use `Scheduler` registration and inspection methods. The current registry is bounded to 10,000 jobs and preserves the following product behavior:

- `add(job)` rejects duplicates; it never replaces implicitly.
- `find(job_id) -> Job | None` and `get(job_id) -> Job` inspect jobs.
- `list_jobs() -> list[Job]` returns a new list in lexical job-ID order.
- `enable(job_id, updated_at)` and `disable(job_id, updated_at)` update scheduling eligibility.
- `remove(job_id) -> Job` removes future registry ownership and returns the job.
- `contains(job_id)` and `count()` inspect registry state.

Removal does not interrupt a handler. The standalone registry permits ID reuse after removal; the manual scheduler rejects reuse while an execution with that ID remains active.

## `chronos.executor` — Internal

`InlineExecutor` and `ExecutionOutcome` are not extension points in `0.4.0`. The scheduler invokes trusted handlers synchronously, contains handler exceptions as the safe category `handler-error`, and makes no timeout-enforcement claim. A future executor interface requires a separately verified public design.

## `chronos.events` — Experimental

### `ChronosEvent`

A validated lifecycle payload with:

- `kind`;
- bounded `job_id` or an empty ID for scheduler lifecycle events;
- `time_domain`, `has_scheduled_time`, and `scheduled_time_ms`;
- actual UTC and monotonic start/end observations;
- monotonic `duration_ms`;
- `attempt`;
- safe `error_category`.

Kinds are exported as `EVENT_REGISTERED`, `EVENT_SCHEDULED`, `EVENT_STARTED`, `EVENT_SUCCEEDED`, `EVENT_FAILED`, `EVENT_MISFIRED`, `EVENT_SKIPPED`, `EVENT_COALESCED`, `EVENT_OVERLAP_QUEUED`, `EVENT_OVERLAP_SKIPPED`, `EVENT_RETRIED`, `EVENT_CANCELLED`, `EVENT_SCHEDULER_STARTED`, and `EVENT_SCHEDULER_STOPPED`.

`coalesced_count` and `coalesced_truncated` are meaningful only for `EVENT_COALESCED`. A truncated count is a bounded known lower bound, not a claim that the complete backlog was enumerated.

### `EventDispatcher(max_listeners)` — Internal

Stores zero through the internal limit of 64 synchronous listeners. It retains no event queue or history. Scheduler consumers use `Scheduler.add_listener`, `listener_count`, and `listener_failure_count`; direct dispatcher construction and emission are unsupported.

See `docs/events.md` for field semantics, ordering, reentrancy, retention, and security boundaries.

## `chronos.policy` — Experimental

This configuration/calculation surface remains pure. `JobPolicies(misfire, overlap, retry)` bundles the three factory-created policies. Construct individual policies with the named factory functions; direct `MisfirePolicy`, `OverlapPolicy`, and `RetryPolicy` constructors and raw kind/bound constants are Internal. Explicit job factories accept the bundle; scheduler dispatch implements skip/fire-once/catch-up, forbid/queue-one, no-retry, fixed retry, and exponential retry under documented combination limits.

### `MisfirePolicy`

- `skip_misfires(grace_period)`
- `fire_once_misfires(grace_period)`
- `catch_up_misfires(grace_period, max_catch_up_count, max_evaluation_steps)`
- `action_for_lateness(lateness) -> str`
- `dispatch_limit(available_occurrences, lateness) -> int`
- `evaluation_limit(available_occurrences) -> int`

Grace uses milliseconds and an inclusive boundary. Per-job catch-up dispatch is capped by `MAX_CATCH_UP_COUNT` (1,024) and evaluation by `MAX_CATCH_UP_EVALUATION_STEPS` (10,000). The scheduler additionally applies the same numeric ceilings globally across all catch-up jobs in one tick; later jobs remain due when the global budget is exhausted.

`default_job_policies()` returns fire-once with maximum grace, forbid, and no-retry. Chronos makes defensive policy copies internally; `copy_job_policies` is not public. Fixed and exponential retry are accepted except with catch-up or queue-one. Catch-up is accepted except for completion-anchored fixed-delay jobs.

### `OverlapPolicy`

`forbid_overlap()` retains no pending occurrence. `queue_one_overlap()` retains at most one planned occurrence observed by a same-thread nested tick. Both have `max_concurrent_runs = 1`; an `allow` configuration is rejected until a concurrent executor and shared-state safety are verified.

### `RetryPolicy`

- `no_retry()`
- `fixed_retry(delay, max_attempts)`
- `exponential_retry(base_delay, maximum_delay, max_attempts)`
- `should_retry_after(completed_attempt) -> bool`
- `delay_before_attempt(attempt) -> Duration`

Attempts include the initial execution and are capped by `MAX_RETRY_ATTEMPTS` (64). Exponential delay saturates at the configured maximum without integer overflow. See `docs/policies.md` for exact semantics and current non-integration limits.

## `chronos.scheduler` — Experimental

### `Scheduler(clock, max_jobs, max_listeners=16)`

Creates an application-owned manual scheduler with injected `Clock`, bounded `JobRegistry`, bounded synchronous listeners, and inline executor.

- `state() -> str`
- `start()` / `stop()`
- `add(job) -> None` / `remove(job_id) -> Job`
- `enable(job_id)` / `disable(job_id)`
- `list_jobs() -> list[Job]`
- `next_run_utc(job_id) -> UtcInstant | None`
- `next_run_monotonic(job_id) -> MonotonicInstant | None`
- `next_retry_monotonic(job_id) -> MonotonicInstant | None`
- `is_completed(job_id) -> bool`
- `add_listener(listener) -> None`
- `listener_count() -> int`
- `listener_failure_count() -> int`
- `tick() -> TickResult`

`TickResult` exposes `succeeded`, `failed`, `skipped`, `misfired`, `policy_skipped`, `catch_up_dispatched`, `coalesced`, `coalesced_truncated`, `overlap_queued`, `overlap_skipped`, `retry_dispatched`, `retries_scheduled`, and `dispatched()`.

`stop()` is terminal and idempotent. With no active callback it stops immediately. From an active inline handler it marks the scheduler as stopping, lets that handler return, then stops without starting remaining snapshot, retry, or queued-overlap work. There is no force-cancel, restart, background join, or execution-timeout API in the manual scheduler.

Exact registration boundaries are inclusive; recurring calculation is exclusive. UTC eligibility uses wall time, while delay/interval eligibility and fixed-delay completion use monotonic time. Due work is ordered UTC-domain first, then monotonic-domain; within a domain it uses planned time then lexical job ID. See `docs/scheduler.md` for lifecycle, mutation, shutdown, and provisional missed-run behavior.

## Supported consumer imports

For a dependency aliased as `chronos`:

```nox-fragment
from chronos.clock import Clock, FakeClock
from chronos.cron import CronSchedule, CronTrigger, parse
from chronos.errors import ChronosError, CronParseError, CronSearchLimitError, DuplicateJobError, EventListenerLimitError, InvalidDurationError, InvalidEventError, InvalidJobError, InvalidPolicyError, JobNotFoundError, SchedulerStateError, TimeRangeError
from chronos.events import ChronosEvent, EVENT_CANCELLED, EVENT_COALESCED, EVENT_FAILED, EVENT_MISFIRED, EVENT_OVERLAP_QUEUED, EVENT_OVERLAP_SKIPPED, EVENT_REGISTERED, EVENT_RETRIED, EVENT_SCHEDULED, EVENT_SCHEDULER_STARTED, EVENT_SCHEDULER_STOPPED, EVENT_SKIPPED, EVENT_STARTED, EVENT_SUCCEEDED
from chronos.job import Job, JobContext, JobMetadata, make_fixed_delay_job, make_fixed_delay_job_with_policies, make_monotonic_job, make_monotonic_job_with_policies, make_utc_job, make_utc_job_with_policies
from chronos.policy import JobPolicies, MisfirePolicy, OverlapPolicy, RetryPolicy, catch_up_misfires, default_job_policies, exponential_retry, fire_once_misfires, fixed_retry, forbid_overlap, no_retry, queue_one_overlap, skip_misfires
from chronos.scheduler import Scheduler, TickResult
from chronos.system_clock import SystemClock
from chronos.time import MAX_MS, MIN_MS, Duration, MonotonicInstant, UtcInstant
from chronos.trigger import DelayTrigger, FixedDelay, FixedRateTrigger, MonotonicTrigger, OnceTrigger, UtcTrigger
```

These dependency-qualified imports describe the intended package surface, but external `noxc add` consumption remains blocked by `NXL-007`. Repository examples use checkout-local module names until that resolver issue is fixed and external-consumer integration tests pass.

## Contract verification

`tests/api_contract_test.nox` imports every allowlisted name through the current checkout-local module form. It fixes the observable contracts for checked time arithmetic, both clock implementations, trigger boundaries, cron matching, policy bounds, all six job factories, event kind values, handler context, scheduler inspection/mutation, lifecycle, and tick results. CI executes the same contract test independently on LLVM and QBE.

The test intentionally does not import Internal symbols. It is a source-checkout contract, not evidence that dependency-qualified imports work; that separate package-consumer gate remains blocked by `NXL-007`.
