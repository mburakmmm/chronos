# Nox capability matrix

Last updated: 2026-11-13
Chronos phase: 3 (`0.3.0` implementation complete, unreleased)

This document separates documentation findings from executable verification. A documented API is not marked fully verified until an appropriate Chronos proof of concept compiles and runs.

## Toolchain snapshot

| Item | Observed value | Status |
|---|---|---|
| Compiler | `noxc 2.1.111` | latest local verification; original Phase 0 evidence used 2.1.0 |
| Host | Darwin 27.2.0 arm64 | verified locally |
| LLVM driver | `/usr/bin/clang` | present; compile/run POC verified |
| C driver | `/usr/bin/cc` | present |
| QBE | `~/.nox-lang/bin/qbe` | present; compile/run POC verified |
| Project profile | hosted by default | hosted run and pure freestanding check verified |
| Git repository | local `main` branch | initialized after explicit sandbox approval |

## Package and module capabilities

| Capability | Evidence | Status |
|---|---|---|
| `nox.json` project discovery | Minimal projects fetched, checked, and ran with Nox 2.1.0 | verified |
| Local Git package dependency | Two local packages fetched and pinned by exact commit | verified |
| Dependency alias import | Root `cron.nox` imported as `chronos.cron` | verified |
| Nested source namespace | `chronos/cron.nox` required `chronos.chronos.cron` | verified; rejected for Chronos layout |
| `nox.lock` reproducible pin | Local package refs resolved to exact commits | verified in POC |

## Time capabilities

| API or behavior | Documentation finding | Executable status |
|---|---|---|
| `nox.time.now_ms()` | Unix epoch milliseconds from wall clock; may jump | callable on LLVM/QBE; monotonicity is intentionally not claimed |
| `nox.time.now()` | Current UTC `DateTime` | verified on LLVM/QBE |
| `nox.time.from_epoch_ms(ms)` | Pure UTC conversion | fixed-input probe verified |
| `DateTime.to_epoch_ms()` | UTC calendar to epoch milliseconds | fixed-input round-trip verified |
| `nox.time.instant_now()` | Monotonic interval clock | verified on LLVM/QBE |
| `Instant.elapsed_ms()` | Monotonic elapsed milliseconds | verified on LLVM/QBE |
| `nox.time.boot_ms()` | Monotonic counter including device suspend | difference measurement verified on LLVM/QBE; physical suspend not emulated |
| `nox.time.sleep_ms(ms)` | Outside a task it blocks the thread; inside an async task Nox 2.1.98 suspends only that fiber | latest two-task probe verified on LLVM/QBE |
| Time zones | Not provided by documented `nox.time` | missing; UTC-only MVP |
| Clock capability | Clock-reading APIs unavailable in freestanding profile | pure calendar accepted and clock APIs rejected with `CapabilityNotGranted` |

The documented suspend behavior of `Instant` differs by platform, while `boot_ms()` includes suspend time on documented platforms. Chronos delay semantics will be fixed only after the clock POCs and design decision are complete.

## Concurrency capabilities

| Capability | Documentation finding | Executable status |
|---|---|---|
| `async def`, `spawn`, `Task[T]`, `await` | Supported | verified on LLVM/QBE |
| Task exception propagation | `await` re-raises task failures | verified on LLVM/QBE |
| `Task.cancel()` | Cooperative; observed at an `await` point | verified on LLVM/QBE |
| `Channel[T]` | Typed bounded/rendezvous channel | bounded channel verified on LLVM/QBE |
| `Channel.wait(ms)` | Cooperative bounded timeout/wake | background-command proof verified on LLVM/QBE |
| LLVM scheduler | Multi-core M:N work-stealing | two-worker sleep probe allowed fast task to progress |
| QBE scheduler | Single-threaded cooperative | task-local sleep and channel wake both allowed the peer task to progress on 2.1.98 |
| Class-valued channel messages | `Channel[BackgroundCommand]` command transport | verified on LLVM/QBE with Nox 2.1.98 |
| Direct class spawn arguments | Historical 2.1.0 QBE proof rejected the form | not used by Chronos; current command POC uses channels |
| Execution interruption | Pure computation is not stopped by cooperative task cancellation | verified limitation; no timeout claim |

## Language model capabilities

| Capability | Evidence | Status |
|---|---|---|
| Typed handler fields | Function value stored and invoked from `Job` | verified on LLVM/QBE |
| Closures | Captured adder stored in job list/dictionary | verified on LLVM/QBE |
| Optional values | `Job | None` narrowing | verified on LLVM/QBE |
| Custom errors | `HandlerError(Exception)` raised and caught | verified on LLVM/QBE |
| Structural protocol values | Heterogeneous `list[Trigger]` dispatch | verified on LLVM/QBE |
| Generic inference | Generic identity function inferred from argument | verified on LLVM/QBE |
| Explicit generic call syntax | `identity[str](...)` | rejected by installed 2.1.0 despite current documentation; avoid until resolved |
| Deferred handler mutations | Context collected add/remove requests | verified as language/design POC |

## Test and filesystem capabilities

| Capability | Documentation finding | Executable status |
|---|---|---|
| `noxc test` | Finds and runs `*_test.nox` programs | verified; 1 test program passed |
| `nox.test` assertions | Typed assertion helpers and `TestSuite` | typed assertion helpers verified; `TestSuite` pending |
| `nox.fs` | Hosted filesystem API; synchronous operations | deferred until persistence work |
| `nox.json` | JSON tree and writer APIs; numeric values are floats | deferred until serialization need |

## Evidence log

### P0-PKG-001 — dependency namespace layout

Date: 2026-11-09/10  
Compiler: Nox 2.1.0  
Host: macOS arm64

Results:

```text
root package + import chronos.cron              -> exit 0, root-module
nested package + import chronos.cron            -> exit 1, module not found
nested package + import chronos.chronos.cron    -> exit 0, nested-module
```

Decision: public modules live at package root.

### P0-CAL-001 — pure epoch/calendar round trip

Source: `examples/calendar_probe.nox`  
Expected fixed timestamp: `2024-01-01 00:00:00` and `True`

Results:

```text
noxc check examples/calendar_probe.nox                         -> exit 0
noxc check --profile freestanding examples/calendar_probe.nox  -> exit 0
noxc run --backend llvm examples/calendar_probe.nox            -> exit 0, expected output
noxc run --backend qbe examples/calendar_probe.nox             -> exit 0, expected output
noxc build --backend llvm ...                                  -> exit 0; binary ran successfully
noxc build --backend qbe ...                                   -> exit 0; binary ran successfully
noxc test tests                                                -> 1 passed, 0 failed
```

Observed output from both backend binaries:

```text
2024-01-01 00:00:00
True
```

### P0-TOOL-001 — project command flow

The Phase 0 project has exercised `noxc fmt`, `check`, `test`, `build`, `run`, and `fetch`. With an empty `requires` list, `fetch` reported no dependencies and did not create `nox.lock`.

### P0-TIME-001 — hosted clock APIs

Sources: `proofs/time_capabilities.nox`, `proofs/datetime_validation.nox`, and `proofs/int_overflow.nox`.

Both LLVM and QBE runs completed successfully. The clock probe observed nondecreasing values around a short sleep and exercised `now`, `now_ms`, `boot_ms`, `Instant.elapsed_ms`, and `Duration.as_ms`.

The freestanding check rejected every clock-reading/sleeping call with `CapabilityNotGranted`, while the pure calendar probe type-checked in the same profile.

The invalid-date proof established that Nox 2.1.0 `DateTime` construction does not validate calendar fields. Chronos must validate them before conversion. The integer proof established signed 64-bit wrapping behavior for plain `int`, so Chronos timestamp arithmetic requires explicit overflow checks.

A later pre-epoch proof using `DateTime(1969, 12, 27, ...).to_epoch_ms()` did not complete on the installed toolchain. Chronos therefore rejects negative epoch milliseconds and supports UTC timestamps from Unix epoch `0` forward. This is a reduced, explicit compatibility boundary rather than an unverified historical-date claim.

### P0-HANDLER-001 — handler and trigger representation

Source: `proofs/handler_model.nox`.

The same source ran successfully on LLVM and QBE and produced identical output. It verified typed handler fields, captured closures, job lists/dictionaries, optional narrowing, a custom handler exception, heterogeneous protocol values, inferred generics, and deferred add/remove requests.

An explicit generic call written as `identity[str]("ok")` failed on the installed Nox 2.1.0 with `unknown generic constructor: identity`, although current documentation describes that syntax. Inferred invocation (`identity("ok")`) succeeded on both backends. Chronos will use only the verified form unless the compiler behavior is resolved.

### P0-CONC-001 — tasks, channels, cancellation, and blocking sleep

Sources: `proofs/concurrency_model.nox`, `proofs/scheduler_sleep_probe.nox`, `proofs/qbe_class_spawn_rejection.nox`, and `proofs/background_command_model.nox`.

The portable concurrency proof produced identical output on LLVM and QBE. Task failures crossed `await`, cancellation surfaced at an awaited operation, and a cancelled task containing no `await` completed normally. This confirms that task cancellation cannot enforce a callback timeout.

The original Nox 2.1.0 run printed `fast sleeper` on LLVM and `sleeper fast` on QBE. The same source on Nox 2.1.98 printed `fast sleeper` on both backends. Current Nox documentation and runtime source define task-local `sleep_ms` as fiber suspension on both backends, so the old ordering result is not treated as a robust whole-scheduler blocking proof.

A spawned task with a class argument ran on LLVM and was rejected by QBE under the original 2.1.0 audit. Chronos does not depend on that boundary. On 2.1.98, `proofs/background_command_model.nox` transported class-valued commands through a typed channel, used `Channel.wait(1000)` for cooperative wake, shut down the owned worker, and printed `7` on LLVM and QBE.

This POC verifies wait/wake and command transport primitives only. Chronos background mode remains deferred until one worker can own the full scheduler/job state, provide bounded command responses, recompute earlier deadlines, and expose observable bounded lifecycle handling.

## Minimum Nox version

Not decided. The latest development matrix uses Nox 2.1.111; historical implementation evidence began on 2.1.0. A minimum supported version will be published only after Phase 4 compatibility tests.

## Phase 1 implementation evidence

The typed time and clock slice was verified with:

```text
noxc test tests                                      -> 3 passed, 0 failed
noxc run --backend llvm tests/time_test.nox          -> exit 0
noxc run --backend qbe tests/time_test.nox           -> exit 0
noxc run --backend llvm tests/clock_test.nox         -> exit 0
noxc run --backend qbe tests/clock_test.nox          -> exit 0
noxc check --profile freestanding time.nox           -> exit 0
noxc check --profile freestanding clock.nox          -> exit 0
noxc check --profile freestanding system_clock.nox   -> expected CapabilityNotGranted
noxc run --backend llvm examples/clock.nox           -> exit 0
noxc run --backend qbe examples/clock.nox            -> exit 0
```

The pure time/FakeClock modules remain freestanding-compatible. The production adapter is isolated in `system_clock.nox` so its required `clock` capability does not leak into pure trigger tests.

The pure trigger slice was verified with:

```text
noxc test tests                                       -> 5 passed, 0 failed
noxc run --backend llvm tests/trigger_test.nox        -> exit 0
noxc run --backend qbe tests/trigger_test.nox         -> exit 0
noxc run --backend llvm tests/interval_test.nox       -> exit 0
noxc run --backend qbe tests/interval_test.nox        -> exit 0
noxc run --backend llvm examples/triggers.nox         -> exit 0
noxc run --backend qbe examples/triggers.nox          -> exit 0
noxc check --profile freestanding trigger.nox         -> exit 0
```

UTC one-shot values and monotonic interval values are separated by type and protocol. A 100-step deterministic recurrence test confirms strictly increasing fixed-rate results.

The UTC cron slice was verified with:

```text
noxc test tests                                      -> 7 passed, 0 failed
noxc run --backend llvm tests/cron_test.nox          -> exit 0
noxc run --backend qbe tests/cron_test.nox           -> exit 0
noxc run --backend llvm examples/cron_utc.nox        -> exit 0
noxc run --backend qbe examples/cron_utc.nox         -> exit 0
noxc check --profile freestanding cron.nox           -> exit 0
```

Golden tests cover lists, ranges, steps, malformed tokens, expression bounds, minute/hour/day/month/weekday transitions, DOM/DOW combinations, leap day, month length, year rollover, unsatisfiable schedules, overflow, and 50 successive increasing results.

## Phase 2 job/registry evidence

The initial job and registry slice was verified with typed handlers, captured closures, structural UTC/monotonic trigger fields, subclass dispatch, bounded class-valued lists, lexical string comparison, list insertion/removal, and custom job errors on both LLVM and QBE.

The first production-shaped model used `int | None` class fields for scheduled and completion timestamps. It passed `noxc check` but reached the installed Nox 2.1.0 generic unsupported-codegen path when combined with the full job model. A minimal standalone optional-field probe succeeded, so the limitation is recorded narrowly rather than generalized. Chronos uses an explicit time-domain discriminator and `has_last_completion` flag in this model.

```text
noxc test tests                                      -> 9 passed, 0 failed
noxc run --backend llvm tests/job_test.nox          -> exit 0
noxc run --backend qbe tests/job_test.nox           -> exit 0
noxc run --backend llvm tests/registry_test.nox     -> exit 0
noxc run --backend qbe tests/registry_test.nox      -> exit 0
noxc run --backend llvm examples/registry.nox       -> exit 0
noxc run --backend qbe examples/registry.nox        -> exit 0
noxc check --profile freestanding job.nox           -> exit 0
noxc check --profile freestanding registry.nox      -> exit 0
```

## Phase 2 UTC manual-scheduler evidence

The first manual scheduler slice verifies injected clocks, inclusive registration boundaries, forward/backward UTC clock jumps, strictly-exclusive recurrence, explicit lifecycle, deterministic due ordering, completed one-shot retention, parsed cron attachment, inline exception containment, reentrant add/remove, stale generation rejection, active ID reuse protection, stop-during-callback behavior, and a bounded 100-jobs-due-at-once case.

A helper that accepted `list[DueItem]` and called `items.insert(...)` passed type checking but reached Nox 2.1.0's unsupported codegen path. Moving insertion into `_collect_due`, where the list is a local owned value rather than a function parameter, compiled and ran on LLVM and QBE. Chronos does not mutate list parameters in this scheduler path.

```text
noxc test tests                                      -> 11 passed, 0 failed
noxc run --backend llvm tests/executor_test.nox     -> exit 0
noxc run --backend qbe tests/executor_test.nox      -> exit 0
noxc run --backend llvm tests/scheduler_test.nox    -> exit 0
noxc run --backend qbe tests/scheduler_test.nox     -> exit 0
noxc run --backend llvm examples/poll.nox           -> exit 0
noxc run --backend qbe examples/poll.nox            -> exit 0
noxc check --profile freestanding executor.nox      -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

The monotonic integration extends the same scheduler with elapsed delay, fixed-rate, and fixed-delay coverage. Tests verify that UTC wall jumps do not change monotonic eligibility, fixed-rate anchors do not drift when handlers advance the fake clock, and fixed-delay recurrence uses actual monotonic completion after success or failure. Mixed snapshots use an explicit UTC-before-monotonic domain order rather than comparing unrelated integer clocks.

```text
noxc run --backend llvm tests/job_test.nox          -> exit 0
noxc run --backend qbe tests/job_test.nox           -> exit 0
noxc run --backend llvm tests/scheduler_test.nox    -> exit 0
noxc run --backend qbe tests/scheduler_test.nox     -> exit 0
noxc run --backend llvm examples/once.nox           -> exit 0
noxc run --backend qbe examples/once.nox            -> exit 0
noxc run --backend llvm examples/every.nox          -> exit 0
noxc run --backend qbe examples/every.nox           -> exit 0
noxc run --backend llvm examples/cancel.nox         -> exit 0
noxc run --backend qbe examples/cancel.nox          -> exit 0
noxc check --profile freestanding job.nox           -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

## Phase 2 lifecycle-event evidence

The lifecycle slice verifies closure-valued listener lists on LLVM and QBE, a configurable 0–64 listener bound, synchronous registration-order delivery, per-listener exception containment, saturating failure counting, and rejection of scheduler mutation during event delivery. The scheduler retains no event queue/history. Deterministic fake-clock tests distinguish planned time from actual UTC observations and derive success/failure duration from monotonic observations. A handler exception containing a secret marker is exposed only as `handler-error`.

```text
noxc test tests                                      -> 13 passed, 0 failed
noxc run --backend llvm tests/events_test.nox       -> exit 0
noxc run --backend qbe tests/events_test.nox        -> exit 0
noxc run --backend llvm tests/scheduler_events_test.nox -> exit 0
noxc run --backend qbe tests/scheduler_events_test.nox  -> exit 0
noxc run --backend llvm examples/events.nox         -> exit 0
noxc run --backend qbe examples/events.nox          -> exit 0
noxc check --profile freestanding events.nox        -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

## Phase 3 pure-policy evidence

The first Phase 3 slice verifies bounded misfire decisions, inclusive millisecond grace, separate catch-up dispatch/evaluation caps, forbid/queue-one overlap configuration, rejection of concurrent allow mode, total-attempt retry semantics, and overflow-safe capped exponential delay. The module is pure and does not yet alter scheduler dispatch.

```text
noxc test tests                                      -> 14 passed, 0 failed
noxc run --backend llvm tests/policy_test.nox       -> exit 0
noxc run --backend qbe tests/policy_test.nox        -> exit 0
noxc run --backend llvm examples/policies.nox       -> exit 0
noxc run --backend qbe examples/policies.nox        -> exit 0
noxc check --profile freestanding policy.nox        -> exit 0
```

## Phase 3 job-policy and misfire evidence

Jobs defensively copy `JobPolicies`; legacy factories install fire-once/max-grace, forbid, and no-retry defaults, while explicit policy-aware factories accept custom bundles. Scheduler tests verify exact-boundary dispatch, skip, fire-once inside/outside grace, day-long forward jumps, fixed-rate anchor preservation, unsupported-policy atomic rejection, misfired/skipped events, and a per-item wall-clock recheck after a callback moves UTC backward.

Attempting to add a trailing optional `JobPolicies | None = None` argument to the exported job factories exposed a new cross-module default-argument `TypeMismatch` despite `job.nox` itself passing type checking. Chronos retained the existing factory signatures and added explicit `_with_policies` variants. This and earlier Nox issues are tracked in `NOX_LIMITATIONS.md`.

```text
noxc test tests                                      -> 15 passed, 0 failed
noxc run --backend llvm tests/job_test.nox          -> exit 0
noxc run --backend qbe tests/job_test.nox           -> exit 0
noxc run --backend llvm tests/scheduler_policy_test.nox -> exit 0
noxc run --backend qbe tests/scheduler_policy_test.nox  -> exit 0
noxc run --backend llvm examples/misfire.nox        -> exit 0
noxc run --backend qbe examples/misfire.nox         -> exit 0
noxc check --profile freestanding job.nox           -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

## Phase 3 bounded catch-up evidence

Catch-up tests enumerate fixed-rate and UTC cron occurrences from their original anchors, dispatch no more than the configured count, bound evaluation separately, and jump directly to the first future occurrence. Exact coalesced counts and truncated lower bounds are distinguished in events and tick results. Removing a job during the first catch-up callback invalidates remaining snapshot work.

```text
noxc test tests                                      -> 15 passed, 0 failed
noxc run --backend llvm tests/scheduler_policy_test.nox -> exit 0
noxc run --backend qbe tests/scheduler_policy_test.nox  -> exit 0
noxc run --backend llvm examples/catch_up.nox       -> exit 0
noxc run --backend qbe examples/catch_up.nox        -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

## Phase 3 bounded overlap evidence

Queue-one tests verify that a same-thread nested tick retains only the earliest next fixed-rate occurrence, discards a later observed overlap, and never recursively starts an unrelated job. Forbid drops the observed fixed-rate and UTC-cron occurrence without incrementing execution count. Completion-anchored fixed-delay produces no synthetic pre-completion occurrence. Removing the active job drops its queued slot and reports the queued planned time in the cancellation event. All overlap state is per job and finite; no concurrent executor or cross-thread safety is claimed.

```text
noxc test tests                                      -> 16 passed, 0 failed
noxc run --backend llvm tests/scheduler_overlap_test.nox -> exit 0
noxc run --backend qbe tests/scheduler_overlap_test.nox  -> exit 0
noxc run --backend llvm examples/queue_one.nox      -> exit 0
noxc run --backend qbe examples/queue_one.nox       -> exit 0
noxc check --profile freestanding events.nox        -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

## Phase 3 bounded fixed-retry evidence

Fixed retry tests verify monotonic delay deadlines, attempts one through the configured total cap, original occurrence identity across attempts, late single dispatch, success, exhaustion, removal, and explicit deadline-overflow failure. Regular recurrence is suspended during retry and resumes from the unchanged fixed-rate anchor or terminal fixed-delay completion. Catch-up-plus-retry and queue-one-plus-retry configurations fail atomically. Execution and retry events expose bounded attempt/deadline data without raw exception payloads.

```text
noxc test tests                                      -> 17 passed, 0 failed
noxc run --backend llvm tests/scheduler_retry_test.nox -> exit 0
noxc run --backend qbe tests/scheduler_retry_test.nox  -> exit 0
noxc run --backend llvm examples/retry.nox          -> exit 0
noxc run --backend qbe examples/retry.nox           -> exit 0
noxc check --profile freestanding events.nox        -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

## Phase 3 bounded exponential-retry evidence

Exponential scheduler tests verify base delay, doubling, maximum-delay saturation across repeated attempts, terminal success, and a separate exhaustion chain. The scheduler reuses the same single monotonic deadline state as fixed retry; it adds no retry collection or background waiter. Catch-up and queue-one combinations remain atomically rejected for both retry modes.

```text
noxc test tests                                      -> 17 passed, 0 failed
noxc run --backend llvm tests/scheduler_retry_test.nox -> exit 0
noxc run --backend qbe tests/scheduler_retry_test.nox  -> exit 0
noxc run --backend llvm examples/exponential_retry.nox -> exit 0
noxc run --backend qbe examples/exponential_retry.nox  -> exit 0
noxc check --profile freestanding scheduler.nox     -> exit 0
```

## Phase 3 deterministic shutdown evidence

The shutdown matrix verifies stop-before-start, idempotent terminal events, restart/tick rejection, pending-retry suppression, queued-overlap suppression, and invalidation of the remaining bounded catch-up snapshot after a handler requests stop. An active inline handler returns and records its outcome; no later callback starts. The test contains no real sleep or background task and completed on both backends without a hang.

```text
noxc version                                         -> noxc 2.1.98
noxc test tests                                      -> 18 passed, 0 failed
noxc run --backend llvm tests/scheduler_shutdown_test.nox -> exit 0
noxc run --backend qbe tests/scheduler_shutdown_test.nox  -> exit 0
noxc run --backend llvm proofs/background_command_model.nox -> exit 0, 7
noxc run --backend qbe proofs/background_command_model.nox  -> exit 0, 7
```

Manual mode therefore has a complete drain-current shutdown contract without claiming interruption, timeout enforcement, or a production background scheduler. Cooperative non-interruption of pure work is tracked as NXL-006.

## Phase 4 compatibility baseline

The 2026-11-14 Nox 2.1.111 local matrix ran all 18 deterministic test programs and all 16 executable examples on both LLVM and QBE. Eleven clock-independent library modules type-checked in the freestanding profile on both backends. `system_clock.nox` passed hosted checking and produced the expected `CapabilityNotGranted` errors for `now_ms()` and `boot_ms()` under freestanding.

The scheduler sleep probe printed `fast sleeper`, the bounded command-channel proof printed `7`, and the cancellation proof ended with `49995000` on both backends. The exact development platform and unsupported platform rows are recorded in `docs/compatibility.md`.

[GitHub Actions run 43460710827](https://github.com/mburakmmm/chronos/actions/runs/43460710827) repeated that full matrix successfully on Linux x64, Linux arm64, macOS arm64, and Windows x64 for commit `a8211b0`. This is execution evidence only for those runner architectures and Nox 2.1.111; it does not imply support for untested platforms or Nox versions.
