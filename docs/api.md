# Chronos public API

Status: experimental (`0.2.0` development).

Only APIs listed here are intended for public use. Leading-underscore functions and everything under `proofs/` are internal validation artifacts.

## `chronos.errors`

### `ChronosError`

Base class for Chronos-specific errors.

### `InvalidDurationError`

Raised when a duration or duration multiplier violates a nonnegative/positive duration contract.

### `TimeRangeError`

Raised before a timestamp or duration operation would overflow, underflow, reverse a monotonic interval, or construct an invalid monotonic value.

Callers should branch on the exception class, not message text.

### Job errors

- `InvalidJobError`: invalid job configuration, bounded resource violation, or registry invariant failure.
- `DuplicateJobError`: an ID is already present; `job_id` contains the rejected ID.
- `JobNotFoundError`: an operation targeted an absent ID; `job_id` contains that ID.
- `SchedulerStateError`: an operation is invalid for the scheduler lifecycle; `state` contains the observed state.
- `InvalidEventError`: an event or listener-capacity configuration violates the event contract.
- `EventListenerLimitError`: listener registration exceeded the scheduler's configured capacity; `limit` contains that capacity.
- `InvalidPolicyError`: a policy kind, bound, attempt, delay, or occurrence count violates the finite policy contract.

## `chronos.time`

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

## `chronos.clock`

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

## `chronos.system_clock`

### `SystemClock`

Production `Clock` implementation:

- UTC comes from `nox.time.now_ms()`.
- monotonic elapsed time comes from suspend-inclusive `nox.time.boot_ms()`.

This module requires Nox's hosted `clock` capability and is unavailable in the freestanding profile.

## `chronos.trigger`

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

## `chronos.cron`

### `parse(expression) -> CronSchedule`

Parses the bounded five-field UTC dialect documented in `docs/cron.md`. Malformed input raises `CronParseError`, which records the field name and bounded offending token.

### `CronSchedule.next_fire_after(reference) -> UtcInstant`

Returns the first UTC minute boundary strictly after `reference`. The algorithm jumps calendar fields and days rather than scanning every minute.

If a syntactically valid expression has no match within eight calendar years or 100,000 transitions, it raises `CronSearchLimitError`. Timestamp overflow raises `TimeRangeError` and is distinct from both parse and search errors.

`CronField.values` contains normalized sorted unique values. `CronField.wildcard` is true only for a field written exactly as `*`; enumerating a full range remains restricted syntax for DOM/DOW semantics.

`next_fire_at_or_after(reference)` preserves a matching exact minute boundary. `matches(candidate)` reports whether a minute-aligned UTC instant matches the schedule.

### `CronTrigger(schedule)`

Adapts an already parsed `CronSchedule` to the optional-return `UtcTrigger` protocol without parsing the expression again. Search-limit and time-range failures remain explicit exceptions.

## `chronos.job`

### Job construction

- `make_utc_job(job_id, name, trigger, handler, enabled, created_at, metadata) -> Job`
- `make_monotonic_job(job_id, name, trigger, handler, enabled, created_at, metadata) -> Job`
- `make_fixed_delay_job(job_id, name, schedule, registered_at, handler, enabled, created_at, metadata) -> Job`
- `make_utc_job_with_policies(..., policy_config) -> Job`
- `make_monotonic_job_with_policies(..., policy_config) -> Job`
- `make_fixed_delay_job_with_policies(..., policy_config) -> Job`

The factories create the supported UTC or monotonic job subtype. Original factories install default policies; `_with_policies` variants require `JobPolicies`. `Job.policy_config()` returns a defensive copy. `Job` itself is the shared registry/executor view; direct construction of the base class is internal.

`job_id` is 1–128 ASCII bytes using letters, digits, `.`, `-`, `_`, or `:`. Names are 1–256 UTF-8 bytes. Each job owns a defensive copy of at most 16 `JobMetadata` entries; keys are bounded identifiers and values are at most 256 bytes.

Handlers have the verified type `(JobContext) -> None`. A context carries `job_id`, an explicit `time_domain` (`utc` or `monotonic`), `scheduled_time_ms`, and a positive attempt number. The domain must be checked before interpreting the millisecond value.

`record_success` and `record_failure` retain only the latest fixed status, bounded safe error category, completion timestamp, and total execution count. Arbitrary results, exception messages, and history are not retained.

### Trigger access

- `trigger_kind() -> str`
- `time_domain() -> str`
- `next_utc_after(reference) -> UtcInstant | None`
- `next_utc_at_or_after(reference) -> UtcInstant | None`
- `next_monotonic_after(reference) -> MonotonicInstant | None`
- `next_monotonic_at_or_after(reference) -> MonotonicInstant | None`
- `next_monotonic_after_completion(completed_at) -> MonotonicInstant`

Calling the wrong-domain method raises `InvalidJobError`.

`make_fixed_delay_job` stores a `FixedDelay` configuration and calculates its first monotonic deadline from `registered_at`. Only fixed-delay jobs support `next_monotonic_after_completion`; the manual scheduler calls it after both successful and failed handlers.

## `chronos.registry`

### `JobRegistry(max_jobs)`

Creates an application-owned in-memory registry. `max_jobs` must be between 1 and 10,000.

- `add(job)` rejects duplicates; it never replaces implicitly.
- `find(job_id) -> Job | None` and `get(job_id) -> Job` inspect jobs.
- `list_jobs() -> list[Job]` returns a new list in lexical job-ID order.
- `enable(job_id, updated_at)` and `disable(job_id, updated_at)` update scheduling eligibility.
- `remove(job_id) -> Job` removes future registry ownership and returns the job.
- `contains(job_id)` and `count()` inspect registry state.

Removal does not interrupt a handler. The standalone registry permits ID reuse after removal; the manual scheduler rejects reuse while an execution with that ID remains active.

## `chronos.executor`

### `InlineExecutor`

`execute(job, context) -> ExecutionOutcome` invokes the trusted handler synchronously. Handler exceptions are contained and represented only by `succeeded = false` and the safe category `handler-error`. The executor does not calculate triggers, record history, spawn work, or claim timeout enforcement.

## `chronos.events`

### `ChronosEvent`

A validated lifecycle payload with:

- `kind`;
- bounded `job_id` or an empty ID for scheduler lifecycle events;
- `time_domain`, `has_scheduled_time`, and `scheduled_time_ms`;
- actual UTC and monotonic start/end observations;
- monotonic `duration_ms`;
- `attempt`;
- safe `error_category`.

Kinds are exported as `EVENT_REGISTERED`, `EVENT_SCHEDULED`, `EVENT_STARTED`, `EVENT_SUCCEEDED`, `EVENT_FAILED`, `EVENT_MISFIRED`, `EVENT_SKIPPED`, `EVENT_COALESCED`, `EVENT_OVERLAP_QUEUED`, `EVENT_OVERLAP_SKIPPED`, `EVENT_CANCELLED`, `EVENT_SCHEDULER_STARTED`, and `EVENT_SCHEDULER_STOPPED`.

`coalesced_count` and `coalesced_truncated` are meaningful only for `EVENT_COALESCED`. A truncated count is a bounded known lower bound, not a claim that the complete backlog was enumerated.

### `EventDispatcher(max_listeners)`

Stores zero through `MAX_EVENT_LISTENERS` (64) synchronous listeners. `add_listener(listener)` rejects capacity overflow. `emit(event)` invokes the listener snapshot in registration order, isolates each exception, and increments a saturating failure count. It retains no event queue or history. Scheduler consumers normally use the forwarding methods on `Scheduler` instead of constructing a dispatcher.

See `docs/events.md` for field semantics, ordering, reentrancy, retention, and security boundaries.

## `chronos.policy`

This configuration/calculation surface remains pure. `JobPolicies` bundles misfire, overlap, and retry settings. Explicit job factories accept the bundle; scheduler dispatch implements skip/fire-once/catch-up with forbid/queue-one and no-retry.

### `MisfirePolicy`

- `skip_misfires(grace_period)`
- `fire_once_misfires(grace_period)`
- `catch_up_misfires(grace_period, max_catch_up_count, max_evaluation_steps)`
- `action_for_lateness(lateness) -> str`
- `dispatch_limit(available_occurrences, lateness) -> int`
- `evaluation_limit(available_occurrences) -> int`

Grace uses milliseconds and an inclusive boundary. Catch-up dispatch is capped by `MAX_CATCH_UP_COUNT` (1,024) and evaluation by `MAX_CATCH_UP_EVALUATION_STEPS` (10,000).

`default_job_policies()` returns fire-once with maximum grace, forbid, and no-retry. `copy_job_policies(source)` makes a defensive copy. Queue-one is accepted by the inline/reentrant scheduler; retry-configured jobs remain rejected. Catch-up is accepted except for completion-anchored fixed-delay jobs.

### `OverlapPolicy`

`forbid_overlap()` retains no pending occurrence. `queue_one_overlap()` retains at most one planned occurrence observed by a same-thread nested tick. Both have `max_concurrent_runs = 1`; an `allow` configuration is rejected until a concurrent executor and shared-state safety are verified.

### `RetryPolicy`

- `no_retry()`
- `fixed_retry(delay, max_attempts)`
- `exponential_retry(base_delay, maximum_delay, max_attempts)`
- `should_retry_after(completed_attempt) -> bool`
- `delay_before_attempt(attempt) -> Duration`

Attempts include the initial execution and are capped by `MAX_RETRY_ATTEMPTS` (64). Exponential delay saturates at the configured maximum without integer overflow. See `docs/policies.md` for exact semantics and current non-integration limits.

## `chronos.scheduler`

### `Scheduler(clock, max_jobs, max_listeners=16)`

Creates an application-owned manual scheduler with injected `Clock`, bounded `JobRegistry`, bounded synchronous listeners, and inline executor.

- `state() -> str`
- `start()` / `stop()`
- `add(job) -> None` / `remove(job_id) -> Job`
- `enable(job_id)` / `disable(job_id)`
- `list_jobs() -> list[Job]`
- `next_run_utc(job_id) -> UtcInstant | None`
- `next_run_monotonic(job_id) -> MonotonicInstant | None`
- `is_completed(job_id) -> bool`
- `add_listener(listener) -> None`
- `listener_count() -> int`
- `listener_failure_count() -> int`
- `tick() -> TickResult`

`TickResult` exposes `succeeded`, `failed`, `skipped`, `misfired`, `policy_skipped`, `catch_up_dispatched`, `coalesced`, `coalesced_truncated`, `overlap_queued`, `overlap_skipped`, and `dispatched()`.

Exact registration boundaries are inclusive; recurring calculation is exclusive. UTC eligibility uses wall time, while delay/interval eligibility and fixed-delay completion use monotonic time. Due work is ordered UTC-domain first, then monotonic-domain; within a domain it uses planned time then lexical job ID. See `docs/scheduler.md` for lifecycle, mutation, shutdown, and provisional missed-run behavior.

## Consumer imports

For a dependency aliased as `chronos`:

```nox-fragment
from chronos.clock import Clock, FakeClock
from chronos.cron import CronSchedule, CronTrigger, parse
from chronos.events import ChronosEvent, EventDispatcher
from chronos.executor import InlineExecutor
from chronos.job import Job, JobContext, JobMetadata, make_fixed_delay_job, make_fixed_delay_job_with_policies, make_monotonic_job, make_monotonic_job_with_policies, make_utc_job, make_utc_job_with_policies
from chronos.policy import JobPolicies, MisfirePolicy, OverlapPolicy, RetryPolicy
from chronos.registry import JobRegistry
from chronos.scheduler import Scheduler, TickResult
from chronos.system_clock import SystemClock
from chronos.time import Duration, MonotonicInstant, UtcInstant
from chronos.trigger import DelayTrigger, FixedDelay, FixedRateTrigger, OnceTrigger
```
