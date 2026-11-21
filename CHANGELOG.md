# Changelog

All notable changes to Chronos will be documented in this file.

The project uses Semantic Versioning, including explicit documentation of breaking changes during the `0.x` series.

## Unreleased

### Added

- Phase 5 `0.5.0-dev` persistence boundary with bounded data-only `StoredJobDefinition` values, a scheduler-independent `JobStore` protocol, explicit format versions, and optimistic compare-and-swap revisions.
- Retained Nox 2.1.111 SQLite capability proof for file reopen, explicit commit/rollback, constraint recovery, and prepared parameter binding on LLVM/QBE, plus an isolated Linux x64 CI job.
- Experimental single-owner `SQLiteJobStore` with transactional schema initialization, prepared values, atomic create/update/delete revision guards, deterministic load, explicit close, fail-closed decoding, and redacted backend errors.
- LLVM/QBE SQLite adapter integration coverage for reopen recovery, stored handler key/configuration, stale writes, conditional delete, malformed rows, unsupported record/schema versions, and SQL-shaped data.
- Optional persistence architecture, API, security, crash-window, and delivery-boundary documentation without claiming scheduler integration or restart delivery.
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
- Exponential retry scheduler integration with overflow-safe doubling, maximum-delay saturation, terminal success, and bounded exhaustion tests.
- Compiling exponential retry example for LLVM and QBE.
- Deterministic terminal shutdown coverage for stop-before-start, pending retry, queued overlap, and multi-item catch-up snapshots on LLVM and QBE.
- A portable background-command proof using cooperative `Channel.wait(ms)`, class-valued channel messages, and bounded worker shutdown on Nox 2.1.98.
- Re-audit of retained Nox limitations on 2.1.98: class-list parameter insertion and negative-epoch conversion are resolved; module-alias shadowing and cross-module optional defaults remain open; non-awaiting work remains cooperatively non-interruptible.
- Phase 4 compatibility baseline covering all 18 tests, all 16 examples, and 11 clock-independent freestanding modules on LLVM and QBE with Nox 2.1.98 on macOS arm64.
- Explicit platform matrix that keeps Linux, Windows, and untested architectures unverified instead of inferring support from macOS results.
- Professional GitHub repository surface with a verified quick start, feature/support matrix, documentation map, security and support policies, structured issue forms, pull request checklist, and code ownership.
- Checksum-pinned cross-platform CI for Linux x64/arm64, macOS arm64, and Windows x64, running the full LLVM/QBE test, example, concurrency, and freestanding matrix on Nox 2.1.111.
- First complete cross-platform CI evidence: all four platform jobs passed in GitHub Actions run 43460710827 for commit `a8211b0`.
- Node.js 24-based checkout/Python actions and an explicit Ubuntu 24.04 x64 runner, avoiding deprecated action runtimes and `ubuntu-latest` image drift.
- Reproducible LLVM/QBE benchmark infrastructure for cron parsing, dense/sparse next-fire calculation, and 100/1k/10k scheduler due collection without timing-based CI gates.
- Initial Nox 2.1.111 macOS arm64 baseline showing quadratic due-collection growth, including 299–352 ms no-due and 2,192–2,239 ms all-due collections at 10,000 jobs; no scheduler data structure was changed without follow-up correctness work.
- Measurement-driven job/schedule identity indexes and deterministic composite-key due sorting, reducing the recorded 10,000-job no-due path to 0.04–0.11 ms and all-due collection to 4.8–9.1 ms across two optimized local runs while retaining ordered inspection and lifecycle invariants.
- Separate LLVM/QBE timing-sensitive integration benchmarks for raw wake overshoot, fixed-rate observed lateness, zero planned-anchor drift, and raw/event-observed callback duration, with no CI timing gates or background-worker claim.
- A 1,000-execution deterministic retention regression proving bounded metadata, stable registry/schedule/listener cardinality, synchronous event delivery without a queue, and latest-only safe outcome/error state.
- NXL-007 records the Nox 2.1.111 package self-import resolution gap; external `noxc add` consumption is not advertised until source-root and consumer imports share one safe form.
- A curated `0.4.0` API allowlist with explicit Stable, Experimental, Deprecated, and Internal semantics; registry, executor, dispatcher, concrete job types, scheduler records, raw constants, and helper functions are no longer presented as supported extension points.
- NXL-008 records Nox's documented lack of module access control, backed by a cross-module leading-underscore import proof in the LLVM/QBE verification matrix.
- A deterministic public API contract test imports the complete Experimental allowlist and fixes time, clock, trigger, cron, policy, job-factory, event, handler-context, scheduler, and tick-result behavior on LLVM and QBE.
- Locked optional integration examples for Nyx `v0.29.0` and Aether `v0.12.0`, verified with Nox 2.1.186 on LLVM/QBE without adding either framework to the core manifest.
- A separate Linux x64 framework-integration CI job plus explicit request-driven polling, worker-local ownership, idle-progress, latency, and source-overlay limitations.

### Security

- Completed the Phase 4 review of parser/search complexity, secret leakage, callback authority, resource bounds, and arbitrary execution; residual application obligations are recorded in `docs/security.md`.
- Cron syntax now rejects ASCII control characters before tokenization, and `CronParseError.message` no longer interpolates the user-controlled token. Precise bounded tokens remain available through explicit field access.
- Catch-up now has global per-tick ceilings of 1,024 candidates and 10,000 next-occurrence evaluations in addition to per-job policy limits, preventing multiplicative snapshot growth across the 10,000-job registry.

### Breaking changes for pinned development snapshots

No Chronos version has been tagged or published yet. The following changes affect applications pinned to earlier `0.1.0-dev` or `0.2.0-dev` commits:

- Custom `UtcTrigger` and `MonotonicTrigger` implementations must provide inclusive `next_fire_at_or_after` in addition to strictly-exclusive `next_fire_after`; this preserves exact registration-time boundaries.
- Direct construction of `UtcJob`, `MonotonicJob`, `FixedDelayJob`, and base `Job` is no longer supported. Use the source-compatible `make_*` factories or the explicit `make_*_with_policies` variants.
- `JobRegistry`, `RegisteredJob`, `InlineExecutor`, `ExecutionOutcome`, `EventDispatcher`, `ScheduledEntry`, `DueItem`, `CronField`, raw constants, and helper functions are Internal. Use `Scheduler`, job factories, policy factories, cron schedule operations, documented event constants, and scheduler forwarding methods.
- Missed-run behavior is now explicit and bounded. Default factories use maximum-grace fire-once, forbidden overlap, and no retry; applications needing multiple missed executions must select bounded catch-up.
- Aggregate catch-up work is now capped across one tick rather than only per job. Later backlogged jobs remain due and require another application-driven tick after the global budget is exhausted.
- `stop()` is terminal. It drains only the active inline callback and does not provide restart, force-cancel, background join, or execution-timeout semantics.
- `ChronosEvent` and `TickResult` evolved with policy fields and counters and must be treated as scheduler-produced values rather than directly constructed records.
- The supported surface is the curated Experimental allowlist in `docs/api.md`; Nox importability does not make an unlisted symbol public. See the [migration guide](docs/migration-guide.md) for replacements and exact development boundaries.

### Limitations

- Jitter is not implemented; fixed and exponential retry delays are deterministic.
- Retry cannot yet be combined with catch-up or queue-one overlap. Completion-anchored fixed-delay rejects catch-up because it has no missed planned-occurrence sequence.
- Queue-one overlap is verified only for the inline, single-threaded reentrant scheduler model; it is not a concurrent-executor or thread-safety claim.
- Platform coverage outside Linux x64/arm64, macOS arm64, and Windows x64 remains unverified.
- Chronos still rejects UTC timestamps before 1970-01-01 as an explicit public-range decision, although the original Nox negative-epoch runtime issue is resolved in 2.1.98.
- Background scheduling is not a supported Chronos mode yet. Nox wait/wake primitives are verified, but worker ownership, bounded command/response handling, and lifecycle integration remain unimplemented.
- Inline handlers cannot be force-cancelled or given an enforceable execution timeout; terminal shutdown drains only the active callback and starts no later work.
