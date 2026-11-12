# Changelog

All notable changes to Chronos will be documented in this file.

The project uses Semantic Versioning, including explicit documentation of breaking changes during the `0.x` series.

## Unreleased

### Added

- Phase 0 development and release tracking plan.
- Minimal Nox 2.1 project manifest with no third-party dependencies.
- Fixed-input calendar capability probe.
- Initial capability matrix and architecture decision for package module layout.
- Executable LLVM/QBE proofs for time APIs, invalid calendar values, integer overflow, typed handlers, protocols, tasks, channels, cancellation, and blocking sleep.
- UTC cron grammar, time semantics, concurrency boundary, and security threat model documents.
- MIT License.
- Experimental `UtcInstant`, `MonotonicInstant`, and `Duration` types.
- Checked timestamp/duration arithmetic with explicit overflow errors.
- Pure `Clock` protocol and deterministic `FakeClock`.
- Hosted `SystemClock` adapter using UTC wall time and suspend-inclusive monotonic time.
- Deterministic time/clock tests and a compiling clock example for LLVM and QBE.
- Strict/exclusive UTC one-shot and monotonic delay triggers.
- Drift-free fixed-rate calculation and completion-anchored fixed-delay configuration.
- Deterministic trigger/interval tests and compiling examples for LLVM, QBE, and freestanding type-checking.
- Bounded five-field UTC cron parser with normalized fields and precise parse errors.
- Calendar-jumping, strictly-after cron next-fire calculation with DOM/DOW OR semantics, leap-year handling, search horizon, and transition cap.
- Regression coverage for pre-epoch rejection and syntax-based DOM/DOW wildcard behavior.
- Pure `CronTrigger` adapter for attaching a parsed cron schedule without reparsing.
- Bounded typed jobs with explicit UTC/monotonic trigger domains, typed handler contexts, defensive metadata copies, and latest-outcome retention.
- Deterministic application-owned `JobRegistry` with duplicate/missing errors, bounded capacity, lexical listing, enable/disable, and future-schedule removal.
- LLVM/QBE job and registry tests plus a compiling registry example.
- Inclusive registration-time trigger operations that preserve exact one-shot, delay, fixed-rate, and cron boundaries while keeping recurrence strictly exclusive.
- Application-owned UTC manual-tick scheduler with explicit lifecycle, deterministic ordering, completed one-shot retention, parsed cron integration, and bounded due snapshots.
- Inline synchronous executor that contains handler failures without retaining exception payloads or stopping unrelated jobs.
- Reentrant add/remove support through generation-checked snapshot dispatch, including active job-ID reuse protection and stop-during-callback behavior.
- Deterministic scheduler/executor tests and a compiling manual polling example for LLVM and QBE.
- Manual scheduler integration for monotonic one-shot delays and anchor-preserving fixed-rate jobs.
- Dedicated completion-anchored fixed-delay jobs with identical rescheduling after success or handler failure and explicit removal semantics.
- Deterministic mixed-domain ordering that never compares UTC and monotonic integers, plus compiling `once`, `every`, and `cancel` examples.
- Bounded synchronous lifecycle listeners for registration, scheduling, execution, cancellation, and scheduler start/stop transitions.
- Separate planned, actual UTC, actual monotonic, and monotonic-duration event fields with safe failure categories.
- Listener exception isolation, aggregate failure counting, reentrant event-mutation rejection, deterministic tests, and a compiling events example.
- Pure bounded misfire policies for skip, fire-once, and catch-up decisions with explicit millisecond grace and evaluation limits.
- Portable overlap configuration for forbid and queue-one, with unverified concurrent allow mode rejected.
- No-retry, fixed-delay retry, and capped exponential retry configuration with at most 64 total attempts and overflow-safe delay calculation.
- Defensive `JobPolicies` attachment through explicit policy-aware job factories with source-compatible default factories.
- Manual scheduler `skip` and grace-bounded `fire-once` misfire dispatch, misfired/skipped events, and separate tick counters.
- Anchor-preserving rescheduling after policy skip and per-dispatch clock revalidation after backward UTC corrections.
- Root `NOX_LIMITATIONS.md` ledger for actionable Nox compiler/runtime limitations discovered during Chronos work.
- Bounded catch-up dispatch for UTC cron, UTC one-shot, monotonic delay, and fixed-rate jobs with anchor-preserving occurrence snapshots.
- Coalesced occurrence events with bounded known counts and explicit truncation when evaluation work is exhausted.
- Catch-up snapshot invalidation after handler removal and compiling catch-up coverage on LLVM and QBE.
- Bounded per-job queue-one overlap state that retains only the earliest pending occurrence while an inline handler is active.
- Explicit `overlap-queued` and `overlap-skipped` lifecycle events plus corresponding `TickResult` counters.
- Reentrant nested-tick isolation that observes the active job's overlap without recursively dispatching unrelated callbacks.
- Pending-overlap cancellation on removal and recomputation on re-enable, with deterministic LLVM/QBE tests and a compiling queue-one example.
- Bounded fixed-delay handler retries using monotonic deadlines and total-attempt limits.
- Retry attempt propagation through job contexts and execution events, plus `retried` scheduling events and tick counters.
- Deterministic retry precedence that suspends regular recurrence until success or exhaustion, then resumes from the original trigger anchor after terminal completion.
- Explicit retry cancellation, late-retry single dispatch, overflow failure handling, and fixed-rate/fixed-delay recurrence tests on LLVM and QBE.

### Limitations

- Configurable execution policies remain incomplete.
- Exponential retry execution remains gated. Fixed retry cannot yet be combined with catch-up or queue-one overlap. Completion-anchored fixed-delay rejects catch-up because it has no missed planned-occurrence sequence.
- Queue-one overlap is verified only for the inline, single-threaded reentrant scheduler model; it is not a concurrent-executor or thread-safety claim.
- Platform and backend compatibility work is incomplete.
- UTC timestamps before 1970-01-01 are rejected because the installed Nox 2.1.0 negative-epoch calendar conversion did not complete reliably.
