# Security model

Status: Phase 4 review completed and Phase 5 SQLite definition adapter reviewed on 2026-11-20; latest matrix uses Nox 2.1.111.

## Phase 4 review result

The review covered every core module and the optional framework adapters for parser/search complexity, secret leakage, callback authority, resource exhaustion, and arbitrary execution. The core imports no process, shell, filesystem, network, HTTP, serialization, or dynamic-code facility. Nyx/Aether examples attach bounded request-driven polling but expose no Chronos administration route.

| Area | Enforced boundary | Review result |
|---|---|---|
| Cron input | 256 bytes, ASCII, five fields, 128 items, fixed field expansion | Control characters rejected before tokenization; parser performs no I/O or evaluation |
| Cron search | Eight calendar years and 100,000 transitions per next-fire query | Explicit `CronSearchLimitError`; no unbounded minute scan |
| Error reflection | Structured field/token for callers; raw cron token omitted from the default exception message | Prevents default log reflection while retaining precise programmatic diagnostics |
| Scheduler work | At most 10,000 jobs, 1,024 catch-up candidates and 10,000 catch-up evaluations across one tick | Prevents per-job catch-up limits from multiplying into millions of one-tick candidates |
| Retained state | Bounded registry, metadata, listener count, latest-only outcome, one retry and one queued overlap per job | No result, exception, event, retry, or missed-run history |
| Callback authority | Trusted typed handlers/listeners and application-supplied clocks/triggers | Full host-process authority is explicit; no sandbox or forceful timeout claim |
| Arbitrary execution | No string evaluation, shell/process executor, remote endpoint, or executable deserialization | No core arbitrary-code path beyond trusted application-supplied Nox objects |

Two findings were remediated during the review. `SEC-001` removed user-controlled cron tokens from the base exception message and rejects newline, carriage-return, DEL, and other ASCII control characters with an empty diagnostic token. `SEC-002` added global per-tick catch-up dispatch/evaluation ceilings; earlier bounds applied independently to each job and could compose into excessive snapshot work.

## Trust boundary

Chronos runs inside the host process and has the same authority as that process. Only trusted application code may register handlers and listeners or supply custom clock/trigger implementations.

Cron expressions and serialized job configuration are data, never executable Nox or shell text.

The Phase 5 store contract and SQLite adapter contain a handler key. The application-owned registry resolves it against explicitly registered callbacks. Missing keys fail closed. The registry passes configuration as opaque data to the callback, and application code must validate it before use.

Job IDs and `CronParseError.token` are application-visible diagnostic data. They must not contain secrets. Printable cron tokens remain available only through explicit field access; the default exception message does not interpolate them. Job IDs remain present in lifecycle events and duplicate/missing-job errors because they are scheduling identities.

## Required controls

- Never evaluate user-provided strings as Nox code.
- Never pass a cron expression or job string to a shell or operating-system cron.
- Never auto-run jobs during module import.
- Keep scheduler lifecycle application-owned and explicit.
- Reject malformed or oversized cron expressions before expansion.
- Bound cron search, catch-up, retry, overlap queues, event buffers, history, and concurrent work.
- Do not include handler arguments, secrets, or arbitrary exception payloads in events/logs by default.
- Treat persisted job definitions as untrusted input if persistence is added later.
- Keep database paths in trusted application configuration and bind every stored value through prepared statements.
- Reject unknown schema/definition/handler/trigger/policy versions instead of guessing a decoder.
- Do not serialize closures, function pointers, live handles, or connections.
- Do not expose a network listener, remote administration endpoint, or process executor from the core MVP.

## Handler execution

Handlers are trusted code and can perform any action available to the application. Chronos does not sandbox them.

A handler exception is caught at the executor boundary and converted to a bounded safe failure summary. Chronos must not claim it can interrupt pure computation: Nox task cancellation is cooperative and cannot enforce a general callback timeout. Shutdown prevents every later callback from starting but permits the active trusted inline handler to return normally; a non-returning handler can therefore prevent the owning application thread from making progress.

## Resource denial of service

The cron parser uses explicit expression/item/expansion bounds. Next-fire calculation has both a calendar horizon and an iteration cap. The registry and scheduler enforce explicit job and listener-count bounds; due snapshots and retained per-job outcome state are finite. Event delivery is synchronous and retains no queue or history. Events omit job name, metadata, handler arguments/results, and raw exception messages.

One tick admits at most one ordinary/retry candidate per job plus a global maximum of 1,024 catch-up candidates. Catch-up discovery performs at most 10,000 next-occurrence evaluations across all jobs in that tick. When the global budget is exhausted, later catch-up jobs remain due for a later application-driven tick; the scheduler does not silently convert them into ordinary dispatches. Selection is deterministic in schedule-registration order before the resulting candidate snapshot is sorted by domain, planned time, and job ID.

A deterministic 1,000-execution regression covers retention claims together: bounded defensive metadata, constant registry/schedule/listener cardinality, no event buffer, a scalar execution count, and replacement of the latest safe error summary rather than accumulation of exception payloads.

No retry, catch-up, overlap, or task-spawn path may grow without a configured finite maximum.

Fixed and exponential retry retain one deadline, upcoming attempt, and original planned timestamp per job, with no retry list or payload history. Attempts are capped at 64; exponential delay saturates at its configured maximum; and only the safe `handler-error` category is retryable. Misfire skip/fire-once performs at most one dispatch per due job in a tick. Catch-up retains no missed-occurrence queue and reports when its known coalesced count is truncated. Queue-one overlap retains exactly one pending timestamp and one bounded observation cursor per job rather than an occurrence list; later observed overlaps are discarded.

Retries cannot make side effects exactly once. Applications must make side-effecting handlers idempotent or use their own transactional deduplication because a handler may commit an effect before raising.

## Residual risks and application obligations

- A trusted handler, listener, clock, or custom trigger can read process secrets, perform I/O, mutate external state, consume CPU/memory, or block forever. Chronos does not sandbox application code.
- Inline execution means handler and synchronous listener latency delays the owning poll/request path. Nox cooperative cancellation cannot enforce a timeout for non-awaiting work.
- A caller can repeatedly invoke `tick()` and therefore repeatedly spend the documented finite work budget. Rate limiting the external polling boundary belongs to the application.
- Public `0.x` values are ordinary mutable Nox objects. Applications must not mutate internal fields or share a scheduler across workers/threads as if it were synchronized.
- Job IDs, handler keys, serialized configuration, printable cron diagnostic tokens, and event timing are observable to application code. Do not put credentials or private payloads in identifiers, expressions, names, metadata, or store records.
- In-memory operation provides no crash durability, delivery guarantee, cross-process coordination, or exactly-once side effects. Side-effecting handlers require application-level idempotency.

## Verification evidence

`tests/cron_test.nox` verifies input length, malformed syntax, control-character rejection, exact structured tokens, and omission of user-controlled tokens from the base exception message. `tests/scheduler_policy_test.nox` constructs multiple maximum-count catch-up jobs, verifies that one candidate snapshot stops at the global dispatch ceiling, and proves deferred work remains due on the next tick. Existing executor, event, job, retention, retry, overlap, shutdown, and API-contract tests cover safe handler categories, listener isolation, bounded metadata/history, finite policy state, terminal lifecycle, and supported surface behavior on LLVM and QBE.

## Persistence and distributed work

The experimental SQLite adapter is data-only. It uses fixed SQL plus parameterized values, validates loaded rows, rejects unsupported versions, and replaces raw backend diagnostics with a fixed message. Its database path is trusted configuration, its connection is single-owner, and it provides no encryption; configurations must not contain secrets.

Forced crash/power-loss, migration failure, file-permission, path-confinement, backup/restore, and secret-management reviews remain mandatory before a scheduler durability claim. Remote execution and distributed coordination are still outside the MVP. Exactly-once execution is not promised.
