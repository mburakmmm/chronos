# Security model

Status: Phase 0 threat model.

## Trust boundary

Chronos runs inside the host process and has the same authority as that process. Only trusted application code may register executable handlers.

Cron expressions and serialized job configuration are data, never executable Nox or shell text.

## Required controls

- Never evaluate user-provided strings as Nox code.
- Never pass a cron expression or job string to a shell or operating-system cron.
- Never auto-run jobs during module import.
- Keep scheduler lifecycle application-owned and explicit.
- Reject malformed or oversized cron expressions before expansion.
- Bound cron search, catch-up, retry, overlap queues, event buffers, history, and concurrent work.
- Do not include handler arguments, secrets, or arbitrary exception payloads in events/logs by default.
- Treat persisted job definitions as untrusted input if persistence is added later.
- Do not serialize closures, function pointers, live handles, or connections.
- Do not expose a network listener, remote administration endpoint, or process executor from the core MVP.

## Handler execution

Handlers are trusted code and can perform any action available to the application. Chronos does not sandbox them.

A handler exception is caught at the executor boundary and converted to a bounded safe failure summary. Chronos must not claim it can interrupt pure computation: Nox task cancellation is cooperative and cannot enforce a general callback timeout. Shutdown prevents every later callback from starting but permits the active trusted inline handler to return normally; a non-returning handler can therefore prevent the owning application thread from making progress.

## Resource denial of service

The cron parser uses explicit expression/item/expansion bounds. Next-fire calculation has both a calendar horizon and an iteration cap. The registry and scheduler enforce explicit job and listener-count bounds; due snapshots and retained per-job outcome state are finite. Event delivery is synchronous and retains no queue or history. Events omit job name, metadata, handler arguments/results, and raw exception messages.

No retry, catch-up, overlap, or task-spawn path may grow without a configured finite maximum.

Fixed and exponential retry retain one deadline, upcoming attempt, and original planned timestamp per job, with no retry list or payload history. Attempts are capped at 64; exponential delay saturates at its configured maximum; and only the safe `handler-error` category is retryable. Misfire skip/fire-once performs at most one dispatch per due job in a tick. Catch-up uses explicit dispatch and evaluation caps, retains no missed-occurrence queue, and reports when its known coalesced count is truncated. Queue-one overlap retains exactly one pending timestamp and one bounded observation cursor per job rather than an occurrence list; later observed overlaps are discarded.

Retries cannot make side effects exactly once. Applications must make side-effecting handlers idempotent or use their own transactional deduplication because a handler may commit an effect before raising.

## Deferred persistence and distributed work

Persistence, remote execution, and distributed coordination are outside the MVP. If added, they require validation, parameterized database operations, explicit crash/delivery semantics, least-privilege credentials, and a separate security review. Exactly-once execution is not promised.
