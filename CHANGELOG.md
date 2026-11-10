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

### Limitations

- The current manual scheduler accepts UTC jobs only; monotonic delay/fixed-rate and completion-based fixed-delay integration remain incomplete.
- Platform and backend compatibility work is incomplete.
- UTC timestamps before 1970-01-01 are rejected because the installed Nox 2.1.0 negative-epoch calendar conversion did not complete reliably.
