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

### Limitations

- No public scheduling API exists yet.
- Platform and backend compatibility work is incomplete.
