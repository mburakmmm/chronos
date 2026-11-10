# AGENTS.md — CHRONOS
## Nox-native scheduling, timers, cron expressions, and background jobs

> Binding engineering instructions for AI coding agents working on **Chronos**, an independent scheduling and job-execution library for the Nox programming language.
>
> **Product definition:** Chronos is a small-to-medium **APScheduler / schedule / croniter-inspired** toolkit: one-shot and repeating timers, cron/calendar scheduling, job registration, deterministic next-run calculation, execution policies, and optional persistence. It is **not** a distributed workflow engine, operating-system cron replacement, or full task queue.
>
> **Naming:** The package, namespace, documentation and releases must use **Chronos** (`chronos`). Never introduce unrelated framework branding.

---

# 1. Mission and non-goals

Create a Nox-native scheduling library that is:
- **Correct about time:** UTC instants, monotonic delays, time zones, daylight saving transitions, and clock jumps have distinct semantics.
- **Predictable:** every trigger produces a deterministic next fire time when given a reference time and configuration.
- **Safe:** bounded execution, explicit error handling, no silent job loss claims, no unsafe callback invocation.
- **Small:** no mandatory Redis, PostgreSQL, web server, native daemon, or cloud account.
- **Composable:** usable in scripts, CLIs, Nyx/Aether servers, and standalone workers without importing those frameworks.
- **Testable:** fake clock, deterministic trigger tests, no flaky sleeps in core unit tests.
- **Honest:** only promise persistent, concurrent, async, or multi-process scheduling after verification and integration tests.

### Initial scope

1. One-shot delayed jobs and jobs scheduled at a UTC timestamp.
2. Fixed-delay and fixed-rate recurring jobs.
3. Pure cron expression parser and next-fire-time calculator.
4. In-process scheduler with start, stop, tick/poll, cancellation.
5. Job metadata, execution result, errors, retry/misfire/overlap policy.
6. Public API, examples, and comprehensive tests.

### Deferred scope

- Durable persistent job store.
- Time-zone database and IANA zone handling.
- Distributed coordination, leader election and leasing.
- Multi-worker task queue and remote execution.
- Complex calendars, business-day scheduling.
- UI dashboard, REST administration API.
- Automatic OS service installation.
- Exactly-once execution claims.
- Automatic execution of shell strings or untrusted code.

---

# 2. First action: verify the actual Nox platform

Before coding, read:
- `https://github.com/mburakmmm/nox-lang` and `https://noxlang.com`
- current Chronos repository and its README/AGENTS.md/tests
- `docs/stdlib/time.md`
- `docs/language/concurrency.md` and actual scheduler/task APIs
- `docs/stdlib/os.md`, `docs/stdlib/fs.md`, `docs/stdlib/json.md`, `docs/stdlib/test.md`
- database drivers only if implementing optional persistence
- package conventions (`nox.json`, `nox.lock`), compiler/tooling docs

Run `noxc version`. Verify every proposed Nox type, callback, closure, protocol, generic, exception, thread/task, channel, cancellation, and synchronization primitive with a compiling proof of concept.

Record evidence in `docs/capabilities.md`:
- API, source, compiler version, tested backend, verified/limited/missing.
- Minimum Nox version and platform profile.
- Whether clock, threading, filesystem and network capabilities are available.
- Differences between LLVM and QBE backends.

## Verified baseline from Nox stdlib documentation (recheck against installed compiler)

- `nox.time.now_ms()` returns Unix epoch milliseconds using **wall-clock time**, which can jump.
- `nox.time.now()` returns a **UTC** `DateTime`.
- `nox.time.from_epoch_ms(ms)` converts Unix epoch milliseconds to UTC `DateTime`.
- `DateTime` exposes `year`, `month`, `day`, `hour`, `minute`, `second`, `to_str()` and `to_epoch_ms()`.
- `nox.time.instant_now()` returns a **monotonic** `Instant`.
- `Instant.elapsed_ms()` and `Instant.elapsed()` measure monotonic elapsed time.
- `Duration(ms)` and `Duration.as_ms()` represent millisecond duration.
- `nox.time.sleep_ms(ms)` **blocks the current thread**.
- Under Nox's documented QBE single-thread scheduler, blocking sleep can block the entire program; other workers may continue under the default multi-core scheduler.
- The documented `DateTime` is **UTC only**; `nox.time` explicitly documents **no time-zone support**.
- Clock-reading functions require Nox's `clock` capability and are unavailable in freestanding profiles; pure calendar conversion is available without clock access.
- `nox.test` and `noxc test` support test suites.
- `nox.process.Command.run()` is synchronous, has an explicit timeout, and executes a program with argument arrays (not shell interpretation); do not make subprocess execution a mandatory scheduler primitive.

**Unverified at design time:** cancellation of spawned Nox tasks, monotonic deadline APIs beyond elapsed measurement, nonblocking timers, thread-safe callback queues, channels across all backends, synchronization primitives, signal handling, wall-clock change notifications, IANA tzdata, robust local time conversions, persistent transactional stores, OS wake timers. These require source inspection and executable tests.

---

# 3. Non-negotiable rules

1. **Nox-native:** no Python-like code presented as real Nox.
2. **No fabricated APIs:** verify Nox callbacks, task spawning, cancellation, atomics and time-zone support.
3. **Never modify Nox compiler/runtime/stdlib without explicit user approval.**
4. **Separate scheduling decisions from execution.** Pure trigger evaluation must not sleep or spawn tasks.
5. **Use monotonic time for elapsed delays and scheduling wait intervals; UTC epoch time for calendar deadlines.**
6. **No local-time cron without verified time-zone rules.** UTC-only cron is an acceptable and preferred MVP.
7. **No exactly-once guarantees** for in-process or distributed execution.
8. **No silent catch-up storms.** Missed executions require an explicit misfire policy and upper bound.
9. **No uncontrolled overlaps.** Define behavior when a job is still running at the next trigger.
10. **No busy loops.** Scheduler polling must use bounded waits and a wake-up strategy supported by Nox.
11. **No hidden global scheduler.** Applications own scheduler lifecycle.
12. **No implicit persistence.** In-memory schedules are lost on process exit.
13. **No unsafe arbitrary code execution from job definitions.**
14. **No secrets in logs, job metadata, error reports, or serialized schedules.**
15. **No automatic cross-process coordination claims.**
16. **No dependency on Nyx, Aether, Aura, Feather, Nova, Rune or Noxen in the core.**
17. **No unbounded retry loops, task spawning, or retained execution history.**
18. **Every public feature must have tests and a compiling example.**
19. **Public API is versioned and documented.**
20. **Report unsupported platforms and limitations honestly.**

---

# 4. Architecture and boundaries

```text
Application
   |
Chronos public API
   |
   +-- chronos.time          UTC instants, durations, clock abstraction
   +-- chronos.trigger       one-shot / interval / cron / calendar triggers
   +-- chronos.cron          pure cron parser and next-fire computation
   +-- chronos.job           job definitions, state and identifiers
   +-- chronos.policy        overlap, misfire, retry, jitter, limits
   +-- chronos.scheduler     in-process lifecycle and dispatch
   +-- chronos.executor      explicit execution adapter
   +-- chronos.events        lifecycle events, optional observability
   |
   +-- chronos.store         optional persistence abstraction (later)
   +-- chronos.timezone      optional IANA time-zone adapter (later)
   +-- chronos.distributed   optional coordination (much later)
```

**Dependency direction:**
- `time`, `cron`, `trigger`, `policy`, and `job` must remain independently testable.
- `cron` and `trigger` must not import scheduler/executor.
- `scheduler` orchestrates triggers, policies, and executor.
- `executor` must not implement cron semantics.
- Persistence must not be required by the in-memory scheduler.
- Framework adapters must be separate packages/examples.
- No cyclic imports, mutable process-global registries, or hidden singleton timers.

## Suggested repository layout

```text
chronos/
  AGENTS.md
  README.md
  LICENSE
  CHANGELOG.md
  CONTRIBUTING.md
  nox.json
  nox.lock                   # only if applicable
  docs/
    architecture.md
    capabilities.md
    api.md
    time-semantics.md
    cron.md
    scheduler.md
    jobs.md
    policies.md
    concurrency.md
    persistence.md
    timezones.md
    security.md
    compatibility.md
    roadmap.md
    migration-guide.md
  chronos/                   # adjust for verified Nox module layout
    time.nox
    clock.nox
    cron.nox
    trigger.nox
    interval.nox
    job.nox
    policy.nox
    scheduler.nox
    executor.nox
    events.nox
    errors.nox
    store.nox                # optional future
    timezone.nox             # optional future
  tests/
    cron_test.nox
    interval_test.nox
    trigger_test.nox
    scheduler_test.nox
    policy_test.nox
    clock_test.nox
    regression_test.nox
  examples/
    once.nox
    every.nox
    cron_utc.nox
    cancel.nox
    retry.nox
    poll.nox
  benchmarks/
  .github/workflows/
```

This tree is a suggestion, not evidence of valid import paths. Do not create empty placeholder modules.

---

# 5. Core time model

## 5.1 Distinct types and semantics

Define concepts explicitly:
- **Instant (UTC epoch):** absolute wall-clock timestamp, preferably integer milliseconds.
- **Duration:** nonnegative elapsed milliseconds (negative durations rejected unless explicitly supported).
- **Monotonic timestamp / clock:** elapsed waiting and interval measurement, not calendar dates.
- **Calendar date-time:** UTC calendar fields, no implicit local timezone.
- **Time zone:** optional verified IANA rules (not present in documented Nox `nox.time`).
- **Scheduled fire time:** planned UTC timestamp.
- **Actual start/end:** observed execution times.
- **Next fire time:** calculated by trigger independently of scheduler state.

Avoid mixing wall-clock and monotonic values in one integer without a distinct type or explicit naming.

## 5.2 Clock abstraction

Provide a clock interface or explicit injected time provider compatible with actual Nox types.

Required:
- `now_utc_ms()` or equivalent.
- monotonic elapsed time measurement where supported.
- `FakeClock` for deterministic tests.
- controlled advancement in tests.
- clear handling of wall-clock jumps.

Do not pretend `Instant` can be converted to Unix epoch time.

## 5.3 Time arithmetic and limits

- Check signed 64-bit overflow and underflow when adding milliseconds.
- Define timestamp supported range and error behavior.
- Define behavior for duration `0`, negative duration, very large duration.
- Avoid floating-point timestamps for scheduling decisions.
- Calendar arithmetic must account for leap years and varying month lengths.
- No assumption that every day is exactly 24 hours in local time.
- No leap-second guarantees unless explicitly implemented.
- Preserve millisecond precision in UTC triggers; cron generally resolves at minute granularity initially.
- Reject impossible dates and invalid time fields where constructors don't validate automatically.
- Ensure schedule calculations terminate or return an explicit no-next-fire result.

---

# 6. Trigger contract

Every trigger should implement a conceptual pure operation:

`next_fire_after(reference_utc_ms, inclusive_or_exclusive) -> timestamp | none`

This is **API design pseudocode**, not verified Nox syntax.

Define whether "after" is strictly greater than the reference; **prefer exclusive** to avoid repeated same-time firing.

Trigger types:
1. **Date/once:** a single UTC timestamp.
2. **Delay:** a monotonic delay from registration/start time (must define semantics on scheduler restart).
3. **Fixed-rate interval:** planned times anchored to start; execution duration does not shift future anchors.
4. **Fixed-delay interval:** next run starts a duration after prior completion.
5. **Cron UTC:** calendar-based matching in UTC.
6. **Calendar recurrence / time zones:** future, gated by correctness.

**Critical:** fixed-delay cannot be calculated solely from the previous planned time; it depends on completion state. Keep trigger definitions and execution policy consistent.

All trigger computations:
- Pure where possible.
- Bounded and deterministic.
- No sleep, I/O, callbacks, database reads, or global state.
- Strictly increasing next-fire values for recurring triggers.
- Never return the same timestamp indefinitely.
- Reject unsatisfiable schedules with a documented error or `none`.
- No silent rounding that changes user intent.

---

# 7. Interval and one-shot scheduling

### One-shot

- Run once at or after target UTC time, subject to misfire policy.
- Past timestamps: explicitly run immediately, skip, or error depending on chosen policy.
- After execution, mark completed and remove/retain metadata per retention policy.
- Do not rerun automatically on scheduler restart unless persistent delivery policy explicitly says so.

### Delays

- Delay is elapsed time; use monotonic clock when available.
- `after(5000ms)` is not equivalent to `at(now_ms()+5000)` when wall clock jumps.
- If scheduler only has blocking sleep, document event-loop blocking risk and provide a manual `tick()` mode.

### Fixed-rate intervals

- Anchor to initial schedule start.
- Calculate next time mathematically, not by repeatedly adding intervals in a long loop.
- Avoid drift from callback execution time.
- Handle missed occurrences via explicit policy.
- Validate interval > 0.
- Prevent integer overflow.

### Fixed-delay intervals

- Next run is based on actual prior completion.
- No overlap by default.
- Retry delays and regular schedule delays must not conflict ambiguously.
- Define behavior when execution fails or is cancelled.

### Jitter (optional)

- Explicit jitter window and deterministic injectable RNG in tests.
- Never allow jitter to create a run before an explicitly prohibited boundary.
- Jitter must not defeat overlap limits or max concurrency.
- Document whether jitter applies per run or at registration.

---

# 8. Cron grammar and correctness

Cron is deceptively complex. **Define the exact grammar before coding.**

## 8.1 MVP grammar

Recommended standard **five-field cron** in UTC:

`minute hour day-of-month month day-of-week`

Ranges:
- minute: `0..59`
- hour: `0..23`
- day of month: `1..31`
- month: `1..12`
- day of week: `0..6`, Sunday = `0` (if accepting `7` as Sunday, explicitly document/test)

Supported syntax:
- `*`
- numeric literal (`5`)
- comma-separated lists (`1,3,5`)
- inclusive ranges (`1-5`)
- steps (`*/15`, `1-10/2`)

Optional later:
- month/weekday names (`JAN`, `MON`)
- six-field seconds
- Quartz `?`, `L`, `W`, `#`
- macros (`@daily`, `@weekly`)
- business calendars

**Do not silently accept Quartz syntax as standard cron.**

## 8.2 Day-of-month vs day-of-week

Traditional cron commonly uses OR semantics when both fields are restricted; other implementations use AND. **Choose and document one explicitly.**

Recommended MVP:
- OR when both DOM and DOW are restricted, otherwise match the restricted field.
- Test all combinations.
- Make alternative AND semantics an explicit option only if justified.

## 8.3 Parser requirements

- Reject wrong number of fields.
- Reject empty fields, trailing commas, duplicate separators and invalid tokens.
- Validate step > 0.
- Validate ranges and out-of-range values.
- Reject reversed ranges unless explicitly supported.
- Bound expression length and number of expanded values.
- Normalize to sorted unique allowed values.
- Provide precise field and token error messages.
- Do not use a shell or OS cron to interpret expressions.
- Do not execute any embedded text.
- No regex-only approach that ignores semantic constraints.

## 8.4 Next-fire computation

- Compute from UTC calendar values.
- Use strictly-after reference semantics by default.
- Respect minute boundaries and seconds/milliseconds.
- Avoid naive unbounded minute-by-minute scans for impossible schedules.
- Bound search horizon (e.g., configurable years) and iteration count.
- Validate February 29, 30th/31st day, month changes, year changes, leap years.
- Ensure monotonic increase for successive returned timestamps.
- Distinguish "no match within horizon" from malformed expression.
- Provide deterministic reference examples and golden tests.

## 8.5 Example expectations (conceptual)

- `*/15 * * * *`: every 15 minutes UTC.
- `0 9 * * 1-5`: 09:00 UTC Monday–Friday.
- `0 0 1 * *`: midnight UTC on the first of each month.
- `0 0 29 2 *`: February 29 only in leap years, depending on DOM/DOW rule.
- `0 0 * * 0`: Sunday midnight UTC.

**Never label these as local-time expressions in the MVP.**

---

# 9. Time zones and daylight saving (future)

The documented `nox.time` module has **no timezone support**. Chronos must not invent it.

**MVP:** all cron expressions and calendar triggers use UTC. Display UTC explicitly in help, logs, examples and API docs.

If adding time-zone support later:
- use a verified IANA tzdata source and version;
- support named zones (e.g. `Europe/Istanbul`, `Europe/Berlin`);
- do not rely on fixed UTC offsets as substitutes for zones;
- define ambiguous local times during fall-back: first occurrence, second occurrence, both, or skip;
- define nonexistent local times during spring-forward: skip or shift, with explicit policy;
- define what happens if tzdata changes;
- test half-hour and unusual offsets;
- test southern hemisphere DST;
- test historical and future transition boundaries;
- document limitations of system time-zone APIs;
- never infer a zone from the machine locale without user opt-in.

Avoid bundling a large tz database until the use case and licensing are justified.

---

# 10. Job definition and registry

A job should have:
- stable identifier;
- human-readable name;
- trigger;
- executable handler/callback;
- optional typed arguments or explicit context;
- enabled/disabled state;
- creation and last-update metadata;
- next planned run;
- overlap policy;
- misfire policy;
- retry policy;
- max execution count (optional);
- last result/error summary (bounded);
- tags/labels (optional).

**Do not serialize executable closures or function pointers.** Persistence stores a handler key and serializable configuration; the application registers trusted handler implementations on startup.

### Registry invariants

- Duplicate IDs must error or follow explicit replace semantics.
- Adding/removing jobs while scheduler runs must have defined concurrency behavior.
- Cancelling a scheduled job is not automatically cancellation of an already-running callback.
- Job IDs cannot be reused ambiguously while a prior run remains active.
- No hidden execution on job registration unless requested.
- Disabling a job must not erase execution history unless explicitly configured.
- Removing a job must not accidentally delete unrelated persisted data.
- No unbounded retention of completed jobs or results.

---

# 11. Scheduler lifecycle

The scheduler must have explicit lifecycle states:
- created
- running
- stopping
- stopped
- failed (if unrecoverable)

Public operations (names are candidates, not verified Nox syntax):
- register/add job;
- remove job;
- enable/disable job;
- inspect/list jobs;
- `start()` / `stop()`;
- `tick(now)` or `poll()` for deterministic/manual driving;
- `run_forever()` only where a safe wait/executor implementation is verified.

### Lifecycle rules

- Start is idempotent or produces a documented state error.
- Stop can be graceful or immediate; semantics documented.
- Graceful stop waits only within a bounded timeout where supported.
- Do not lose ownership of spawned work.
- A scheduler may not run callbacks after shutdown has completed.
- Handle jobs added during a wait without sleeping past the new earliest deadline.
- Scheduler state must remain coherent after handler exceptions.
- Avoid reentrant scheduler calls that corrupt internal collections.
- Protect shared job state when Nox worker concurrency is actually used.
- No hidden global background threads.
- Provide manual tick mode as a fallback on restricted backends.

### Wait strategy

- Calculate nearest deadline.
- Use bounded wait or verified wake primitive.
- Re-evaluate on new job, cancellation, clock jump and completion.
- Avoid polling at millisecond frequency without reason.
- Never call `nox.time.sleep_ms` from a callback-sensitive single-thread event loop without evaluating QBE behavior.
- If no safe nonblocking wait exists, document limitations and expose externally driven scheduler ticks.

---

# 12. Executor and concurrency

Separate **which job is due** from **how a job runs**.

Initial executor modes:
- **Inline/synchronous:** simplest and most portable; callback blocks scheduler.
- **Spawned-task executor:** only if Nox's task API, safety and cancellation behavior are verified.

Optional later:
- bounded worker pool;
- external process executor with explicit trusted program/args;
- persistent queue adapter.

### Execution invariants

- Catch handler errors and record job failure without corrupting scheduler state.
- Do not let one failing callback permanently stop all unrelated jobs unless configured.
- No unbounded spawning of tasks.
- Max concurrent jobs and per-job concurrency limits must be enforced.
- No simultaneous callback invocation for same job by default.
- Explicit execution timeout only if real cancellation or isolation is supported.
- Never advertise timeout enforcement if it only measures elapsed time after callback returns.
- Preserve job ordering semantics when several jobs share the same fire time.
- Avoid deadlock if callback adds/removes jobs.
- Do not hold scheduler locks while executing user callbacks.
- No cross-worker sharing of unsafe DB connections.
- No silent thread safety claims.

---

# 13. Misfires, overlaps and coalescing

Define the policies **before** implementing scheduler dispatch.

### Misfire: a planned run time has passed

Recommended policies:
- `skip`: drop missed occurrences, schedule next future fire.
- `fire_once`: run one catch-up execution.
- `catch_up`: run a bounded number of missed occurrences.

Rules:
- Configurable grace period, with explicit units.
- Maximum catch-up count and time budget.
- No unbounded loops after laptop sleep or long downtime.
- No promise of execution at the exact requested millisecond.
- Record scheduled time and actual start time separately.

### Overlap: prior execution still running

Recommended policies:
- `forbid` (default): do not start a second instance.
- `queue_one`: remember at most one pending occurrence.
- `allow`: only with explicit max concurrent runs.

Rules:
- Document whether skipped overlaps count as missed executions.
- Never queue unbounded occurrences by default.
- No data races in per-job running count.
- Enforce policies identically across trigger types.

### Coalescing

When several runs were missed:
- combine into one run or run up to bounded N;
- record how many were coalesced when feasible;
- avoid changing the cron schedule anchor;
- use deterministic test clocks.

---

# 14. Retry and failure policy

Retries are **separate** from recurrence.

Recommended:
- no retry by default;
- fixed retry delay;
- exponential backoff with upper bound;
- optional bounded jitter;
- maximum attempts.

Rules:
- Clearly define whether retry attempts count toward a job's execution limit.
- Retries must not silently overlap the next regular scheduled occurrence.
- Use idempotency guidance for side-effecting jobs.
- Never retry permanently invalid schedules.
- Distinguish handler failure, scheduler failure, cancellation and infrastructure failure.
- Avoid logging secret exception payloads.
- Retain bounded error summaries.
- Do not promise exactly-once side effects.
- Retry policy cannot substitute for transactional outbox or idempotent operations.

---

# 15. Persistence (optional, post-MVP)

The core in-memory scheduler is **ephemeral**. A process restart loses jobs unless a durable store is explicitly configured.

Potential stores:
- SQLite for a single-process service;
- PostgreSQL for multi-instance persistence (not automatically distributed execution);
- MySQL/MariaDB if justified.

**Do not make Feather mandatory**: use existing `nox.db` drivers or a separate optional Feather adapter.

Persist:
- job ID, name, trigger specification, handler key, arguments/configuration, policy, enabled state, next run, version;
- execution history only with explicit retention limits.

Do **not** persist:
- function pointers or closures;
- live connections;
- secrets in plaintext by default;
- unbounded exception traces.

### Persistence semantics

- Define atomic write and recovery behavior.
- Define what happens after process crash between dispatch and completion.
- Document **at-most-once vs at-least-once** behavior where applicable.
- Exactly-once cannot be guaranteed merely by storing a row.
- Schema migrations must be explicit and safe.
- Persisted schedules must include timezone/dialect/format version.
- Job handler registry must be restored by application code.
- Support graceful handling of unknown handler keys.
- Use parameterized SQL and transaction boundaries.
- Test crash/restart and corrupted-state recovery.

---

# 16. Distributed scheduling (future, independent approval)

Multiple processes pointing at the same database do **not** automatically form a correct distributed scheduler.

Before implementing:
- define ownership leases and fencing tokens;
- ensure atomic claim of due jobs;
- design clock-skew assumptions;
- define lease renewal, expiry and recovery;
- address duplicate execution after crash;
- define worker identity and heartbeats;
- use real DB transactional primitives;
- test concurrent claims and network partitions;
- document at-least-once delivery and idempotency requirements;
- avoid claims of strict exactly-once.

Do not build Redis/Kafka dependencies into the core.

---

# 17. Public API proposal (conceptual only)

Design for clarity, but **verify Nox syntax and callback support before publishing code**.

Conceptual operations:
- `chronos.once_at(utc_ms, handler)`
- `chronos.after(duration_ms, handler)`
- `chronos.every(interval_ms, handler, policy)`
- `chronos.cron("0 9 * * 1-5", handler, timezone="UTC")`
- `scheduler.add(job)`
- `scheduler.remove(job_id)`
- `scheduler.tick()`
- `scheduler.start()`
- `scheduler.stop()`
- `cron.next_after(reference_utc_ms)`

**All above are pseudocode, not verified Nox calls.**

Prefer:
- explicit constructors and types;
- consistent millisecond units;
- no reflection-dependent decorators;
- no Python `*args/**kwargs`;
- typed job context;
- explicit error/result types compatible with actual Nox;
- small stable API with internal implementation flexibility.

### Public API stability

Maintain:
- `docs/api.md` — stable public functions/types;
- `docs/compatibility.md` — supported Nox versions, backends, platforms;
- `docs/migration-guide.md` — breaking changes;
- `CHANGELOG.md`.

Stability labels:
- Stable;
- Experimental;
- Deprecated;
- Internal.

Use SemVer; document all breaking changes, including 0.x.

---

# 18. Security

- Jobs execute with the authority of the host process; only trusted application code may register executable handlers.
- Never evaluate user-provided strings as Nox code.
- Never execute shell commands from cron expressions.
- No implicit `sh -c` or platform shell usage.
- External process jobs (if implemented) must use explicit program/argument arrays, not interpolated shell strings.
- Never execute user-supplied program paths without validation.
- Protect job administration APIs with application-level authorization.
- Treat persisted job definitions as untrusted until validated.
- Bound cron parser complexity and search horizon.
- Bound job counts, execution history, retries and concurrent tasks.
- Avoid secret leakage in logs, event payloads, job names and serialized arguments.
- Use least-privilege database accounts for persistent stores.
- No remote code execution, remote management endpoint or network listener in core.
- Do not auto-run jobs on import.
- Ensure shutdown does not leave half-updated state without explicit recovery policy.

---

# 19. Observability and events

Provide structured lifecycle events if Nox types/callbacks allow:
- registered;
- scheduled;
- started;
- succeeded;
- failed;
- skipped;
- misfired;
- retried;
- cancelled;
- scheduler started/stopped.

Each event should include:
- job ID;
- scheduled fire timestamp;
- actual start/end timestamps when applicable;
- duration measured with monotonic time;
- attempt count;
- safe error category;
- optional trace/correlation ID (future).

Rules:
- Events must not contain secret payloads.
- Listener failures must not silently corrupt scheduling.
- Event buffers bounded; define drop/backpressure policy.
- Avoid retaining full result objects indefinitely.
- Provide no-op observability by default.
- Integrate with application logging without requiring Rune or a web framework.

---

# 20. Testing plan

Use `nox.test` and `noxc test`; compile every executable example.

## Pure trigger tests (no real sleeps)

- One-shot past/future/exact boundary.
- Interval fixed-rate vs fixed-delay.
- 0/negative/overflow intervals.
- Millisecond precision.
- Strictly increasing next-fire values.
- Clock jumps forward/backward.
- Cron syntax: wildcards, lists, ranges, steps, malformed tokens.
- Cron minute/hour/day/month/weekday boundaries.
- Day-of-month vs day-of-week policy.
- Leap years and February 29.
- Month lengths and year rollover.
- Unsatisfiable schedules and search horizon.
- Cron 5-field vs unsupported 6/7-field expressions.
- UTC correctness and rejection of unsupported timezones.

## Scheduler tests (fake clock)

- Registration, duplicate IDs, removal, enable/disable.
- Due jobs, future jobs, exact-boundary jobs.
- Multiple jobs due at same instant.
- Add/remove during tick.
- Callback exception and recovery.
- Graceful stop and lifecycle idempotence.
- Misfire skip/fire-once/bounded catch-up.
- Overlap forbid/queue-one/allow with caps.
- Retry/backoff/exhaustion.
- Bounded history and concurrency.
- Shutdown while running.
- No busy-loop invariant.

## Integration tests

- Real one-shot delay with tolerance; avoid brittle exact-time assertions.
- Real recurring job over a bounded short period.
- QBE single-thread scheduler behavior.
- LLVM/default scheduler behavior.
- Windows/macOS/Linux where claimed.
- No-clock/freestanding compilation of pure cron functions if supported.
- Persistence crash/restart tests **only when implemented**.
- Distributed contention tests **only when implemented**.

### CI rules

- No external database for MVP.
- Pure tests must be fast and deterministic.
- Separate timing-sensitive integration tests from unit tests.
- Never claim a test passed unless executed.
- Never weaken or delete tests merely to green CI.
- Add a regression test for every bug.
- Report unsupported backends rather than silently skipping.

---

# 21. Performance and resource usage

- Benchmark cron parsing, next-fire computation, due-job lookup, scheduling 100/1k/10k jobs.
- Use an efficient due-time structure (e.g. min-heap) only if it measurably helps and Nox supports a correct implementation.
- Avoid scanning all jobs on every millisecond tick.
- Avoid repeated cron parsing at every trigger evaluation.
- Bound memory retained for job metadata, errors, and history.
- Avoid unbounded task creation or recursive retry chains.
- Document scheduler accuracy as best-effort, not real-time.
- Measure wake latency, drift and overhead separately.
- Benchmark both compiler backends where relevant.
- Never compromise correctness or shutdown safety for throughput.

---

# 22. Documentation requirements

`README.md` must contain:
- purpose and explicit non-goals;
- Nox compiler version and verified platforms;
- installation using real `nox.json` conventions;
- one-shot example that compiles;
- interval example that compiles;
- UTC cron example that compiles;
- manual tick mode and background mode availability;
- callback and error behavior;
- time semantics, UTC-only limitation, DST caveats;
- misfire, overlap and retry defaults;
- lifecycle and shutdown;
- in-memory persistence limitation;
- public API support matrix;
- security and license.

Other docs:
- `time-semantics.md` — wall vs monotonic clocks, UTC and leap years.
- `cron.md` — exact supported grammar and DOM/DOW rule.
- `scheduler.md` — states, waiting, callback execution.
- `policies.md` — misfires, overlap, retries, catch-up caps.
- `concurrency.md` — Nox task/backends and restrictions.
- `persistence.md` — deferred support, durability and crash behavior.
- `timezones.md` — UTC-only MVP and optional future IANA support.
- `compatibility.md` — tested OS/backend/runtime combinations.

**Never publish conceptual pseudocode as executable Nox.** Label unverified API sketches.

---

# 23. Roadmap with exit gates

## Phase 0 — Audit and proof of concept
- Audit Nox clocks, scheduler, callbacks, concurrency, package and tests.
- Compile a clock/handler proof of concept.
- Write capability matrix and architecture decisions.
**Gate:** no critical API assumptions remain unverified.

## Phase 1 — Chronos 0.1: pure time and triggers
- UTC instant/duration wrappers.
- Fake clock.
- One-shot and interval trigger calculations.
- Pure five-field UTC cron parser and next-fire algorithm.
- Exhaustive date/grammar tests.
**Gate:** no real sleep required for core tests.

## Phase 2 — Chronos 0.2: in-process scheduler
- Job registry and lifecycle.
- Manual tick/poll scheduler.
- Synchronous executor.
- Cancellation of pending jobs.
- Basic lifecycle events.
**Gate:** deterministic scheduler tests pass.

## Phase 3 — Chronos 0.3: robust execution policies
- Misfire, overlap, bounded catch-up.
- Retry/backoff, job limits.
- Graceful shutdown and error handling.
- Optional background execution if verified.
**Gate:** no unbounded retries/overlaps and no hidden hangs.

## Phase 4 — Chronos 0.4: portability and integration
- LLVM/QBE behavior validation.
- Windows/macOS/Linux checks.
- Nyx/Aether integration examples without core coupling.
- Performance benchmarks and public API cleanup.
**Gate:** platform support claims match actual CI evidence.

## Phase 5 — Chronos 0.5+: optional persistence
- Separate store interface.
- SQLite persistence first.
- Crash/restart behavior.
- Explicit delivery semantics.
**Gate:** durable semantics and failure recovery tested.

## Phase 6 — Optional advanced scheduling
- IANA timezone support only with verified tzdata.
- Calendar schedules and DST policies.
- PostgreSQL persistent store and optional distributed coordination after separate approval.
**Gate:** independent architecture/security review.

## Phase 7 — Chronos 1.0
- Stable minimal public API.
- Full tests, docs, compatibility matrix, security review.
- SemVer commitment.
- Release only with user approval.
**Gate:** all advertised behavior is verified and reproducible.

---

# 24. Agent workflow

For every request:

1. Restate scope and acceptance criteria.
2. Inspect current Chronos source and tests.
3. Inspect Nox stdlib/source for any required primitive.
4. Compile minimal feature proof where uncertain.
5. Explain time semantics and policy choices.
6. Implement smallest coherent slice.
7. Add deterministic unit tests first.
8. Add integration tests only where needed.
9. Run `noxc fmt` (in place), `noxc check`, `noxc test`, examples, and relevant CI.
10. Review concurrency, clock jumps, UTC/DST, cancellation, retry, resource limits, and secrets.
11. Update docs/API support matrix/changelog.
12. Report files changed, exact commands run, real results and limitations.

If blocked:
- never invent task/timer/clock APIs;
- create a minimal reproduction;
- document the exact missing capability;
- provide a correct reduced-scope alternative (e.g. manual tick or UTC-only);
- request permission before compiler/runtime/native changes.

---

# 25. Definition of Done

- [ ] Valid Nox syntax compiled with current toolchain.
- [ ] Clock semantics explicit and tested.
- [ ] UTC and monotonic time are not confused.
- [ ] Cron grammar documented and enforced.
- [ ] Next-fire calculation is deterministic and bounded.
- [ ] No unbounded catch-up or retry storms.
- [ ] Overlap behavior explicit.
- [ ] Scheduler lifecycle and cancellation semantics tested.
- [ ] QBE/blocking behavior documented.
- [ ] No unverified timezone, task, async, or persistence claims.
- [ ] No hidden global scheduler or mandatory framework dependency.
- [ ] Public API documented and contract-tested.
- [ ] Errors, shutdown, resource bounds and secrets reviewed.
- [ ] Tests and examples actually run.
- [ ] CI claims match executed checks.
- [ ] Remaining limitations listed in final report.

---

# 26. First autonomous implementation assignment

**Build the smallest correct Chronos, not an imaginary full APScheduler clone.**

1. Inspect `nox.time`, Nox task/concurrency docs and implementation, `nox.test`, package layout.
2. Verify `noxc version` and LLVM/QBE differences.
3. Document `now_ms`, `Instant`, `sleep_ms`, UTC `DateTime` and absent timezone support.
4. Implement a pure UTC five-field cron parser and bounded next-fire calculator.
5. Implement one-shot and fixed-rate interval triggers with explicit millisecond semantics.
6. Add a fake clock and exhaustive deterministic tests (including leap years).
7. Build a manual-tick in-memory scheduler with a synchronous executor.
8. Add explicit job IDs, removal, lifecycle, error handling and no-overlap default.
9. Compile and run small Nox examples.
10. Write a backlog for background scheduling, retry/misfire policies, persistence, time zones and distributed mode.
11. Do not modify Nox compiler/runtime or publish releases without user authorization.

**Quality bar:** deterministic UTC scheduling with honest platform support beats a feature-rich scheduler that misses jobs, duplicates work, or cannot compile.
