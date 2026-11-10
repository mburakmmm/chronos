# Manual scheduler

Status: experimental Phase 2 UTC slice for Nox 2.1.0.

## Ownership and lifecycle

`Scheduler(clock, max_jobs)` is an application-owned in-memory object. It creates no global scheduler, thread, task, timer, sleep, or network listener.

Lifecycle states are `created`, `running`, `stopping`, `stopped`, and `failed`.

- `start()` changes `created` to `running` and is idempotent while already running.
- A stopped scheduler cannot restart.
- `stop()` is idempotent after a stop request.
- A stop requested inside the active inline callback enters `stopping`; that callback finishes, the scheduler becomes `stopped`, and no later due callback starts.
- `tick()` is valid only while running.
- An unrecoverable failure while recording an execution outcome changes the scheduler to `failed`.

The application decides when to call `tick()`. Chronos does not sleep or busy-loop.

## Current trigger support

This slice accepts UTC jobs: one-shot jobs and parsed cron schedules wrapped in `CronTrigger`. Adding a monotonic delay or fixed-rate job raises `InvalidJobError` instead of silently using wall time. Monotonic and fixed-delay scheduler integration remains a Phase 2 task.

Initial registration uses the trigger's explicit `next_fire_at_or_after` contract. Therefore a one-shot or cron occurrence exactly equal to registration time remains due, including Unix epoch `0`. Normal recurrence uses strictly-after calculation and cannot repeat the same occurrence.

A past one-shot is retained as completed without execution. A completed job remains inspectable in the bounded registry and cannot run again.

UTC jobs follow wall-clock corrections: a forward jump may make a deadline due on the next tick, while a backward jump cannot make it run before the target wall time. The monotonic counter is not consulted for UTC trigger eligibility.

## Tick and dispatch

Each tick reads the injected clock, builds a finite due snapshot, and orders it by planned UTC timestamp then lexical job ID. Jobs sharing a timestamp therefore have stable total ordering.

The inline executor invokes one trusted handler at a time. It catches handler exceptions and returns the fixed safe category `handler-error`; raw exception text is not retained. The scheduler records the outcome and continues with unrelated due jobs.

When a recurring UTC job is late, this Phase 2 slice dispatches at most one occurrence for that job in the tick and calculates the next occurrence strictly after the later of planned time and observed completion wall time. This bounds catch-up work but is not the final configurable misfire policy; explicit skip/fire-once/catch-up policies belong to Phase 3.

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
