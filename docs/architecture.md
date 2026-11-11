# Chronos architecture

Status: accepted architecture records through the experimental Phase 2 API.

## ADR-001: consumer-facing modules live at the package root

Decision date: 2026-11-10  
Status: accepted by compiling proof of concept

### Context

Nox resolves the first segment of a dependency import as the alias declared in the consuming project's `nox.json`. The remainder is a path inside that dependency.

Chronos needs imports such as:

```nox-fragment
import chronos.cron
```

The repository instructions suggested a `chronos/cron.nox` directory layout, but explicitly required that suggested paths be verified before adoption.

### Proof

Two temporary Git-backed packages and two consuming Nox projects were created with Nox 2.1.0:

1. A dependency containing root-level `cron.nox` compiled and ran through `import chronos.cron`, printing `root-module`.
2. A dependency containing `chronos/cron.nox` failed through `import chronos.cron` with `module not found`.
3. The nested dependency compiled only through `import chronos.chronos.cron`, printing `nested-module`.

The package fetches resolved and pinned the local Git commits in each consumer's `nox.lock`.

### Decision

Consumer-facing Chronos modules will live at the repository root, for example:

```text
clock.nox
cron.nox
trigger.nox
job.nox
policy.nox
scheduler.nox
executor.nox
events.nox
errors.nox
```

Only modules implemented in the active release phase will be created. Empty placeholder modules are prohibited.

Tests and examples remain in their own directories:

```text
tests/
examples/
docs/
benchmarks/
```

The manifest `entry` selects a project program; it does not create the dependency namespace. During Phase 0 it points to a capability probe. It will later point to a representative compiling example when a public Chronos API exists.

### Consequences

- A consumer dependency aliased as `chronos` can use `import chronos.cron`.
- Code inside this repository imports root modules by their project paths, such as `import cron`.
- A nested `chronos/` source directory will not be introduced merely to imitate package names from languages with different module resolution rules.

## Dependency direction

The intended dependency flow is:

```text
time/clock, errors, events
        |
        +--> cron, trigger, policy, job
                         |
                         +--> scheduler --> executor
                                  |
                                  +--> events
```

Constraints:

- Cron and trigger calculation do not import scheduler or executor.
- Scheduler orchestrates triggers, policies, jobs, and an explicit executor.
- Persistence and timezone adapters remain optional and outside the MVP core.
- No cyclic imports, mutable global registry, or hidden scheduler lifecycle.

## ADR-002: handlers are typed values and reentrant mutations are deferred

Decision date: 2026-11-10  
Status: accepted for the manual scheduler design

The LLVM and QBE handler proof verified that Nox 2.1.0 can:

- store typed function values and captured closures in job objects;
- store those jobs in lists and dictionaries;
- store heterogeneous trigger implementations behind a structural protocol;
- use `T | None` and custom exception subclasses;
- catch a handler error and continue operating on unrelated state.

The proof also demonstrated a handler context that can collect deferred mutations. The implemented manual scheduler uses an equivalent snapshot-and-revalidation design that is smaller for the verified inline executor: it never iterates live collections while invoking a callback, and it revalidates a generation token before each later dispatch.

This establishes the initial reentrancy rule:

1. The scheduler never iterates or holds an internal collection mutation guard while invoking user code.
2. Each tick uses a bounded due snapshot ordered by planned UTC time and job ID.
3. Additions made during dispatch wait until the next tick; removals invalidate later snapshot items.
4. Active job ID reuse is rejected until the callback boundary has returned.

The scheduler and registry are application-owned instances. They are not mutable module-level singletons. This avoids Nox's documented worker-local module state behavior and keeps lifecycle explicit.

The proof is `proofs/handler_model.nox`.

## Next decisions

Phase 0 has verified the basic Nox types used for clocks, callbacks, optional values, errors, collections, and portable task/channel examples.

## ADR-003: trigger and scheduler ordering contracts

Decision date: 2026-11-10  
Status: accepted for MVP implementation

### Trigger contract

The default pure operation is strictly exclusive:

```text
next_fire_after(reference_utc_ms) -> timestamp | none
```

A returned timestamp must be greater than the reference. A recurring trigger returning the same timestamp is a contract violation.

Each UTC/monotonic trigger also exposes `next_fire_at_or_after` for initial registration or re-enable. The inclusive operation may return the reference itself; the scheduler never uses it for recurrence.

### One-shot registration

- A future target is scheduled normally.
- A target equal to the registration clock value remains due for the first tick; registration does not accidentally discard an exact-boundary one-shot.
- A past target uses the default `skip` misfire behavior and records the skip when events are available.
- An explicit future misfire policy may request a bounded `fire_once`; there is no implicit catch-up loop.

### Fixed-rate and fixed-delay

Fixed-rate occurrences remain anchored to the initial start:

```text
anchor + k * interval
```

The smallest `k` producing a value strictly after the reference is calculated arithmetically with checked operations. Callback duration never moves the anchor.

Fixed-delay is stateful: its next time is based on actual prior completion plus the configured delay. It is not implemented as a pure fixed-rate trigger and defaults to no overlap.

### Deterministic order

UTC and monotonic integers are never compared as if they shared a time scale. A mixed-domain due snapshot dispatches UTC items before monotonic items. Within one domain, due work is ordered first by its scheduled timestamp and then by lexical job ID. Duplicate job IDs are rejected, so the second key is stable and total for jobs sharing a domain and timestamp.

## ADR-004: numeric and error boundaries

UTC timestamps use epoch milliseconds from `0` through signed `int64` maximum. Durations use nonnegative signed 64-bit milliseconds. All additions and multiplications are checked before evaluation because Nox plain `int` wraps.

- Negative durations are rejected.
- A zero one-shot delay is valid and becomes due once.
- A recurring interval must be greater than zero.
- Overflow/underflow is an explicit time-range error.

The planned error taxonomy uses a `ChronosError` base with specific configuration, time-range, cron-parse/search, duplicate-job, missing-job, scheduler-state, and handler-execution categories. Exact public names will be contract-tested when implemented; callers must branch on error class, not message text.

Cron grammar and search bounds are defined in `docs/cron.md`. Security/resource limits are defined in `docs/security.md`.

## ADR-005: bounded job registry and trigger-domain subtypes

Decision date: 2026-11-10

Status: accepted for Phase 2

The shared `Job` type owns identity, handler, enabled state, bounded metadata, and bounded latest-outcome state. `UtcJob` and `MonotonicJob` store their respective structural trigger protocols and override domain-specific next-fire methods. Public factories construct these subtypes; the base constructor is not a supported consumer API.

The registry is a bounded, lexically ordered list rather than a mutable process-global map. This gives deterministic inspection order, avoids hidden lifecycle, and keeps correctness independent of hash iteration. A future benchmark may justify an additional index without changing the public contract.

Registry removal means future schedule removal only. It does not cancel an executing handler. The standalone registry allows reuse after removal; the manual scheduler retains an active ID guard until the in-flight callback has finished.

## ADR-006: synchronous bounded lifecycle observation

Decision date: 2026-11-10

Status: accepted for Phase 2

The portable scheduler delivers lifecycle events synchronously through a bounded listener collection. There is no queue, event history, replay buffer, worker, or global event bus. Each listener has an independent exception boundary, and only an aggregate saturating failure count is retained.

Event payloads separate scheduled time from actual UTC and monotonic observations. Duration is derived only from monotonic start/end values. Job name, metadata, arguments, results, and raw exception text are excluded.

Event listeners are observational callbacks. Scheduler mutation, lifecycle transitions, and nested ticks during delivery are rejected so event reentrancy cannot invalidate scheduler collections. Inline job handlers keep their generation-checked mutation contract.

## ADR-007: policy configuration precedes dispatch integration

Decision date: 2026-11-11

Status: accepted for the first Phase 3 slice

Misfire, overlap, and retry configuration is implemented first as a pure bounded module. This isolates validation, grace boundaries, attempt semantics, and overflow-safe backoff from scheduler mutation.

Catch-up has separate dispatch-count and evaluation-work caps. Retry counts the initial execution as attempt one. Overlap `allow` is rejected because the current executor is synchronous and no shared-state concurrent execution claim has been verified.

Jobs now own a defensive `JobPolicies` copy. Scheduler integration accepts skip/fire-once/catch-up with forbid and no-retry; completion-anchored fixed-delay excludes catch-up, and other unsupported combinations fail atomically at registration. Misfire rescheduling queries the existing trigger strictly after observed time, preserving cron and fixed-rate anchors instead of synthesizing a new anchor.

Bounded catch-up expands planned occurrences into the same generation-checked due snapshot used by ordinary dispatch. The snapshot contains no more than the configured dispatch count per job. A separate evaluation bound limits backlog inspection; known excess is coalesced, and incomplete counting is explicitly marked truncated. The final next time is queried directly after the tick observation, preventing an unbounded backlog walk.
