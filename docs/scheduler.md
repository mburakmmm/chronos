# Manual scheduler

Status: experimental Phase 2 manual scheduler for Nox 2.1.0.

## Ownership and lifecycle

`Scheduler(clock, max_jobs, max_listeners=16)` is an application-owned in-memory object. It creates no global scheduler, thread, task, timer, sleep, or network listener. Listener capacity may be configured from zero through 64.

Lifecycle states are `created`, `running`, `stopping`, `stopped`, and `failed`.

- `start()` changes `created` to `running` and is idempotent while already running.
- A stopped scheduler cannot restart.
- `stop()` is idempotent after a stop request.
- A stop requested inside the active inline callback enters `stopping`; that callback finishes, the scheduler becomes `stopped`, and no later due callback starts.
- `tick()` is valid only while running.
- An unrecoverable failure while recording an execution outcome changes the scheduler to `failed`.

The application decides when to call `tick()`. Chronos does not sleep or busy-loop.

## Trigger support

The scheduler accepts:

- UTC one-shot jobs and parsed cron schedules wrapped in `CronTrigger`;
- monotonic one-shot delays;
- monotonic fixed-rate recurrence;
- completion-anchored fixed-delay recurrence.

Initial registration uses the trigger's explicit `next_fire_at_or_after` contract. Therefore a one-shot or cron occurrence exactly equal to registration time remains due, including Unix epoch `0`. Normal recurrence uses strictly-after calculation and cannot repeat the same occurrence.

A past one-shot is retained as completed without execution. A completed job remains inspectable in the bounded registry and cannot run again.

UTC jobs follow wall-clock corrections: a forward jump may make a deadline due on the next tick, while a backward jump cannot make it run before the target wall time. The monotonic counter is not consulted for UTC trigger eligibility.

Elapsed jobs use only the monotonic counter for eligibility. Wall-clock jumps do not make a delay or interval early/late. Fixed-rate next times remain anchored to the original trigger anchor even when a callback advances the clock. Fixed-delay next times are calculated from observed monotonic completion, after either success or handler failure.

If a fixed-delay job's first deadline is already past when it is added or re-enabled, exactly one execution becomes due at the observed monotonic time. Chronos does not generate an unbounded first-run catch-up sequence.

## Tick and dispatch

Each tick reads both injected clock domains and builds a finite due snapshot. UTC items are dispatched before monotonic items so unlike numeric domains are never compared. Within each domain, items are ordered by planned timestamp then lexical job ID. Jobs sharing a domain and timestamp therefore have stable total ordering.

The inline executor invokes one trusted handler at a time. It catches handler exceptions and returns the fixed safe category `handler-error`; raw exception text is not retained. The scheduler records the outcome and continues with unrelated due jobs.

Bounded synchronous listeners observe registration, scheduling, execution, cancellation, and scheduler start/stop transitions. Listener failures are counted and isolated from scheduler state and handler outcomes. See `docs/events.md` for payload, ordering, retention, and reentrancy rules.

When a fixed-rate or recurring UTC job is late, this Phase 2 slice dispatches at most one occurrence for that job in the tick and calculates the next anchored occurrence strictly after the later of planned time and observed completion in the matching domain. This bounds catch-up work but is not the final configurable misfire policy; explicit skip/fire-once/catch-up policies belong to Phase 3.

`TickResult` reports succeeded, failed, and stale-snapshot skipped counts. It does not retain handler results.

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
