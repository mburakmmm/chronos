# Concurrency and execution model

Status: Phase 0 architecture decision for Nox 2.1.0.

## Portable baseline

Chronos MVP uses an application-owned manual-tick scheduler and an inline/synchronous executor.

- The application decides when to call `tick` or `poll`.
- Trigger evaluation never spawns tasks or sleeps.
- The inline executor invokes one trusted handler at a time.
- A handler failure is caught and recorded without stopping unrelated jobs.
- There is no hidden global task, worker thread, or scheduler singleton.

This mode is portable across the tested LLVM and QBE backends and avoids relying on an unverified scheduler wake-up primitive.

## Verified Nox task behavior

The Phase 0 concurrency proof ran on both backends and verified:

- `async def`, `spawn`, `Task[T]`, and `await`;
- bounded `Channel[T]` send/receive;
- exception propagation through `await`;
- cooperative `Task.cancel()` behavior;
- completion of cancelled pure work that never reaches an `await` point.

Cancellation is therefore not an execution timeout. Chronos will not advertise callback interruption or timeout enforcement for in-process handlers.

## Backend differences

The LLVM backend uses an M:N scheduler. In the two-worker sleep probe, a fast task progressed while another task was inside `nox.time.sleep_ms`.

The QBE backend is single-threaded and cooperative. In the same probe, `sleep_ms` blocked the scheduler until the sleeping task returned.

For this reason, a portable Chronos background loop must not be implemented as a spawned task that repeatedly calls `sleep_ms`.

QBE also rejected a spawned task whose argument was a class instance, while LLVM accepted it. Portable spawned boundaries must use only types demonstrated on both backends, such as scalar values and channels. Scheduler/job class objects will not be sent directly to a portable spawned worker.

## Background scheduling

Background mode is deferred. It may be added only after all of the following are demonstrated on both claimed backends:

- a bounded, non-busy wait strategy;
- a wake-up path for newly added earlier jobs and cancellation;
- owned task shutdown with bounded waiting;
- safe communication without mutable module globals;
- explicit behavior for callbacks still running during shutdown.

Until then, manual tick is the supported portable lifecycle.

## Reentrancy

User callbacks are invoked without iterating the live registry/schedule collections. A tick dispatches from a finite due snapshot and revalidates generation and current registry state before every callback. Additions become eligible on the next tick; removals invalidate pending snapshot entries. Active ID reuse is rejected until the inline callback returns. See `docs/architecture.md` ADR-002.

A handler may call `tick()` reentrantly. While an inline callback is active, that nested tick evaluates only the active job's next possible occurrence and defers unrelated callbacks to the owning outer tick. `forbid` drops the observed occurrence; `queue-one` stores at most one planned timestamp and never invokes it recursively. This state is bounded and safe for same-thread reentrancy only. It is not protected for calls from another OS thread and is not a concurrent-executor claim.

Fixed retry creates no sleeper or task. The scheduler records one monotonic deadline and the application must call `tick()` at or after it. Attempts remain inline and sequential; regular recurrence is suspended until the chain terminates. Retry therefore adds no concurrent callback or cancellation guarantee.

Fixed-delay completion is sampled only after the inline callback returns. Chronos therefore does not confuse planned time, UTC completion metadata, and monotonic completion used for the next delay.

Lifecycle listeners are synchronous and run in registration order. Their exceptions are isolated per listener, but a slow listener delays inline dispatch. Mutation, start/stop, and nested tick calls from event delivery are rejected; handlers retain the generation-checked mutation behavior above. There is no event worker or unbounded event queue.
