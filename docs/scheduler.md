# Manual scheduler

Status: experimental Phase 3 manual scheduler; latest matrix uses Nox 2.1.111.

## Ownership and lifecycle

`Scheduler(clock, max_jobs, max_listeners=16)` is an application-owned in-memory object. It creates no global scheduler, thread, task, timer, sleep, or network listener. Listener capacity may be configured from zero through 64.

Lifecycle states are `created`, `running`, `stopping`, `stopped`, and `failed`.

- `start()` changes `created` to `running` and is idempotent while already running.
- A stopped scheduler cannot restart.
- `stop()` is idempotent after a stop request.
- A stop requested inside the active inline callback enters `stopping`; that callback finishes, the scheduler becomes `stopped`, and no later due callback starts.
- A stop with no active callback, including before `start()`, reaches `stopped` immediately.
- Terminal shutdown emits `scheduler-stopped` exactly once and rejects every later `start()` or `tick()`.
- `tick()` is valid only while running.
- An unrecoverable failure while recording an execution outcome changes the scheduler to `failed`.

The application decides when to call `tick()`. Chronos does not sleep or busy-loop.

Manual mode owns no worker task, so `stop()` has no background join or graceful-timeout parameter. It provides drain-current semantics only: Chronos never interrupts the active trusted handler, but it revalidates lifecycle before each remaining snapshot dispatch. Thus pending catch-up items, retries, and queued overlaps cannot start after the stop request. Immediate force-cancellation and handler execution timeouts are unsupported because Nox cancellation is cooperative for non-awaiting work.

## Trigger support

The scheduler accepts:

- UTC one-shot jobs and parsed cron schedules wrapped in `CronTrigger`;
- monotonic one-shot delays;
- monotonic fixed-rate recurrence;
- completion-anchored fixed-delay recurrence.

Initial registration uses the trigger's explicit `next_fire_at_or_after` contract. Therefore a one-shot or cron occurrence exactly equal to registration time remains due, including Unix epoch `0`. Normal recurrence uses strictly-after calculation and cannot repeat the same occurrence.

A past one-shot is retained as completed without execution. A completed job remains inspectable in the bounded registry and cannot run again.

UTC jobs follow wall-clock corrections: a forward jump may make a deadline due on the next tick, while a backward jump cannot make it run before the target wall time. The monotonic counter is not consulted for UTC trigger eligibility.

Elapsed jobs use only the monotonic counter for eligibility. Wall-clock jumps do not make a delay or interval early/late. Fixed-rate next times remain anchored to the original trigger anchor even when a callback advances the clock. Fixed-delay next times are calculated from observed monotonic completion after the occurrence's terminal attempt.

If a fixed-delay job's first deadline is already past when it is added or re-enabled, exactly one execution becomes due at the observed monotonic time. Chronos does not generate an unbounded first-run catch-up sequence.

## Tick and dispatch

Each tick reads both injected clock domains and builds a finite due snapshot. UTC items are dispatched before monotonic items so unlike numeric domains are never compared. Within each domain, items are ordered by planned timestamp then lexical job ID. Jobs sharing a domain and timestamp therefore have stable total ordering.

The inline executor invokes one trusted handler at a time. It catches handler exceptions and returns the fixed safe category `handler-error`; raw exception text is not retained. The scheduler records the outcome and continues with unrelated due jobs.

Bounded synchronous listeners observe registration, scheduling, execution, cancellation, and scheduler start/stop transitions. Listener failures are counted and isolated from scheduler state and handler outcomes. See `docs/events.md` for payload, ordering, retention, and reentrancy rules.

An exact-boundary occurrence is not a misfire. A late occurrence uses the job's millisecond-grace policy: `skip` records no execution and advances to the first future anchored occurrence, while `fire-once` dispatches one occurrence when within grace and otherwise skips. `catch-up` enumerates bounded planned occurrences, dispatches up to the configured count, coalesces evaluated excess, and jumps directly to the first future anchored occurrence. Fixed-rate and cron anchors are not shifted. A skipped fixed-delay occurrence uses observed skip time as its next delay base because there is no completion timestamp; fixed-delay rejects catch-up.

The default job configuration preserves the earlier bounded behavior by firing one late occurrence with maximum grace, forbidding overlap, and performing no retry. Queue-one, fixed retry, and exponential retry are supported under their documented combination limits. Every due, catch-up, or retry snapshot item is rechecked against generation, enabled state, attempt, deadline, and matching clock immediately before dispatch, so removal/shutdown invalidates remaining work and a backward UTC correction cannot start a later callback early.

`TickResult` reports `succeeded`, `failed`, total `skipped`, `misfired`, `policy_skipped`, `catch_up_dispatched`, `coalesced`, `coalesced_truncated`, `overlap_queued`, `overlap_skipped`, `retry_dispatched`, and `retries_scheduled` counts. `coalesced` is the known bounded count; a positive truncated-batch count means more backlog existed but was deliberately not enumerated. Deferring an unrelated job during a nested tick is not counted as a skip because the outer tick can still dispatch it. Tick results retain no handler payloads.

## Retry backoff

After a contained handler failure, `fixed_retry(delay, max_attempts)` schedules a constant delay and `exponential_retry(base_delay, maximum_delay, max_attempts)` doubles from the base until the maximum. The selected delay is added to monotonic completion. The scheduler stores one retry deadline, not a queue. `next_retry_monotonic(job_id)` exposes that deadline; regular `next_run_utc`/`next_run_monotonic` returns no regular run while the retry chain owns the job.

Every attempt retains the original occurrence's planned timestamp and domain in `JobContext` and execution events. `retried` instead carries the upcoming monotonic deadline and attempt number. A retry that is polled late executes once and bypasses recurrence misfire policy.

Regular recurrence is suspended for the chain. Success or exhaustion is terminal for that occurrence: one-shot completes, cron/fixed-rate resumes at the first anchored occurrence strictly after terminal completion, and fixed-delay starts from terminal monotonic completion. This prevents retry from overlapping a regular run. Neither retry mode can currently be combined with catch-up or queue-one.

Removal cancels the stored retry deadline. Re-enable discards it and recalculates the regular trigger. A stop requested by the active failing handler completes shutdown without scheduling another attempt. Monotonic deadline overflow is an unrecoverable scheduler failure and is never wrapped.

## Inline overlap

The inline executor normally prevents overlap by construction. A handler can nevertheless advance an injected clock and call `tick()` reentrantly, making a later occurrence observable while the first callback is still active. That nested tick never recursively starts an unrelated job; the outer tick remains its owner.

With `forbid`, the earliest observed overlapping occurrence is discarded and emits `overlap-skipped`. With `queue-one`, the first observed occurrence is retained in one pending slot and emits `overlap-queued`; a later observed overlap is discarded and emits `overlap-skipped`. A queued occurrence becomes the job's next planned run after the active callback returns and is dispatched only by a later outer tick, where normal misfire policy still applies. Skipped overlaps do not increment execution count or outcome history.

Removing a job drops its pending slot and the cancellation event identifies the queued planned time. Disabling suspends dispatch; enabling clears any pending slot and recomputes from the current clock. Stopping during the active callback prevents the queued run from starting. One-shot, delay, and completion-anchored fixed-delay jobs cannot synthesize an occurrence before completion.

The per-job running count and pending slot are verified only for same-thread reentrant callbacks. They provide no cross-thread synchronization or concurrent executor guarantee.

## Mutations during callbacks

Callbacks run without iterating the live registry/schedule collections. The tick uses a due snapshot and revalidates job ID, generation, enabled state, and planned timestamp before each dispatch.

- A job added during a callback is first eligible on the next tick.
- Removing a not-yet-dispatched job invalidates its snapshot item, so its callback never starts.
- Removing the active job removes future scheduling but does not interrupt that callback.
- Reusing the active job ID is rejected until the callback returns.
- A generation token prevents a removed/re-added job from inheriting a stale due item.

This is single-threaded reentrancy safety for the inline executor. It is not a thread-safety or concurrent mutation claim.

## Persistence and accuracy

Registry and schedule state exist only in process memory and are lost on exit. Manual ticks provide best-effort execution at or after a planned time; they do not promise real-time precision, exactly-once side effects, persistence, or cross-process coordination.
