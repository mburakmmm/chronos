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

A handler exception is caught at the executor boundary and converted to a bounded safe failure summary. Chronos must not claim it can interrupt pure computation: Nox task cancellation is cooperative and cannot enforce a general callback timeout.

## Resource denial of service

The cron parser uses explicit expression/item/expansion bounds. Next-fire calculation has both a calendar horizon and an iteration cap. The registry and scheduler enforce an explicit job-count bound; due snapshots and retained per-job outcome state are finite.

No retry, catch-up, overlap, or task-spawn path may grow without a configured finite maximum.

## Deferred persistence and distributed work

Persistence, remote execution, and distributed coordination are outside the MVP. If added, they require validation, parameterized database operations, explicit crash/delivery semantics, least-privilege credentials, and a separate security review. Exactly-once execution is not promised.
