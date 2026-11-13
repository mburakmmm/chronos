# Concurrency and execution model

Status: Phase 3 execution and shutdown decision; reverified with Nox 2.1.111.

## Portable baseline

Chronos MVP uses an application-owned manual-tick scheduler and an inline/synchronous executor.

- The application decides when to call `tick` or `poll`.
- Trigger evaluation never spawns tasks or sleeps.
- The inline executor invokes one trusted handler at a time.
- A handler failure is caught and recorded without stopping unrelated jobs.
- There is no hidden global task, worker thread, or scheduler singleton.

This mode is portable across the tested LLVM and QBE backends and keeps callback ownership explicit.

## Verified Nox task behavior

The Phase 0 concurrency proof ran on both backends and verified:

- `async def`, `spawn`, `Task[T]`, and `await`;
- bounded `Channel[T]` send/receive;
- exception propagation through `await`;
- cooperative `Task.cancel()` behavior;
- completion of cancelled pure work that never reaches an `await` point.

Cancellation is therefore not an execution timeout. Chronos will not advertise callback interruption or timeout enforcement for in-process handlers.

## Current backend findings

The LLVM backend uses a multi-core M:N scheduler. QBE remains single-threaded and cooperative.

Nox 2.1.111 documents and implements `nox.time.sleep_ms()` inside an async task as suspension of only the calling fiber on both backends. The latest two-task probe printed `fast sleeper` on LLVM and QBE. Calling `sleep_ms()` outside an async task still blocks the calling thread.

The earlier Nox 2.1.0 ordering probe was scheduling-order-sensitive and is not retained as evidence that task-local sleep blocks the complete QBE scheduler.

Nox 2.1.111 provides `Channel.wait(ms)` for a cooperative bounded timeout. A proof sends class-valued commands through `Channel[BackgroundCommand]`, wakes a worker, and performs bounded shutdown on both LLVM and QBE. This verifies building blocks, not transfer of a live Chronos scheduler or job registry across a spawned boundary.

## Background scheduling

Background mode remains deferred. The wait/wake and command transport primitives are now verified, but a production mode may be added only after all of the following are integrated and demonstrated on both claimed backends:

- one worker owns all mutable scheduler/job state;
- add/remove/inspect commands have a bounded request/response contract;
- newly earlier jobs and cancellation wake and recompute the deadline;
- the worker task has bounded, observable startup and shutdown;
- explicit behavior for callbacks still running during shutdown.

Until then, manual tick is the supported portable lifecycle.

## Shutdown contract

Manual mode owns no background task and therefore exposes no artificial shutdown wait or timeout parameter. If no callback is active, `stop()` transitions directly to `stopped`. If an inline handler calls `stop()`, the scheduler enters `stopping`, lets only that trusted handler return, records its outcome, emits one terminal `scheduler-stopped` event, and starts no later due, catch-up, retry, or queued-overlap callback.

Repeated stop requests are idempotent. A stopped scheduler rejects `start()` and `tick()` and cannot restart. Pending in-memory schedule metadata may remain inspectable, but it has no execution path after terminal shutdown.

This is cooperative drain-current shutdown, not forceful callback cancellation. Nox task cancellation cannot interrupt non-awaiting work, and Chronos offers no immediate-stop or execution-timeout guarantee for inline handlers. The capability boundary is tracked as NXL-006.

## Reentrancy

User callbacks are invoked without iterating the live registry/schedule collections. A tick dispatches from a finite due snapshot and revalidates generation and current registry state before every callback. Additions become eligible on the next tick; removals invalidate pending snapshot entries. Active ID reuse is rejected until the inline callback returns. See `docs/architecture.md` ADR-002.

A handler may call `tick()` reentrantly. While an inline callback is active, that nested tick evaluates only the active job's next possible occurrence and defers unrelated callbacks to the owning outer tick. `forbid` drops the observed occurrence; `queue-one` stores at most one planned timestamp and never invokes it recursively. This state is bounded and safe for same-thread reentrancy only. It is not protected for calls from another OS thread and is not a concurrent-executor claim.

Fixed and exponential retry create no sleeper or task. The scheduler records one monotonic deadline and the application must call `tick()` at or after it. Attempts remain inline and sequential; regular recurrence is suspended until the chain terminates. Retry therefore adds no concurrent callback or cancellation guarantee.

Fixed-delay completion is sampled only after the inline callback returns. Chronos therefore does not confuse planned time, UTC completion metadata, and monotonic completion used for the next delay.

Lifecycle listeners are synchronous and run in registration order. Their exceptions are isolated per listener, but a slow listener delays inline dispatch. Mutation, start/stop, and nested tick calls from event delivery are rejected; handlers retain the generation-checked mutation behavior above. There is no event worker or unbounded event queue.
