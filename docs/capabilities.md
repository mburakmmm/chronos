# Nox capability matrix

Last updated: 2026-11-10  
Chronos phase: 1 (`0.1.0` development)

This document separates documentation findings from executable verification. A documented API is not marked fully verified until an appropriate Chronos proof of concept compiles and runs.

## Toolchain snapshot

| Item | Observed value | Status |
|---|---|---|
| Compiler | `noxc 2.1.0` | verified locally |
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
| `nox.time.sleep_ms(ms)` | Blocks the current thread | call verified on LLVM/QBE; concurrent scheduler impact POC pending |
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
| LLVM scheduler | Multi-core M:N work-stealing | two-worker sleep probe allowed fast task to progress |
| QBE scheduler | Single-threaded cooperative | sleep probe blocked fast task until sleeper returned |
| `sleep_ms` under QBE | Blocks the sole scheduler thread | verified by ordering probe |
| QBE task value restrictions | Class spawn argument rejected; portable channel/scalar forms succeeded | verified |
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

### P0-HANDLER-001 — handler and trigger representation

Source: `proofs/handler_model.nox`.

The same source ran successfully on LLVM and QBE and produced identical output. It verified typed handler fields, captured closures, job lists/dictionaries, optional narrowing, a custom handler exception, heterogeneous protocol values, inferred generics, and deferred add/remove requests.

An explicit generic call written as `identity[str]("ok")` failed on the installed Nox 2.1.0 with `unknown generic constructor: identity`, although current documentation describes that syntax. Inferred invocation (`identity("ok")`) succeeded on both backends. Chronos will use only the verified form unless the compiler behavior is resolved.

### P0-CONC-001 — tasks, channels, cancellation, and blocking sleep

Sources: `proofs/concurrency_model.nox`, `proofs/scheduler_sleep_probe.nox`, and `proofs/qbe_class_spawn_rejection.nox`.

The portable concurrency proof produced identical output on LLVM and QBE. Task failures crossed `await`, cancellation surfaced at an awaited operation, and a cancelled task containing no `await` completed normally. This confirms that task cancellation cannot enforce a callback timeout.

With `NOX_POOL_WORKERS=2`, the LLVM sleep probe printed `fast sleeper`. QBE printed `sleeper fast`, showing that `sleep_ms` blocked the only scheduler thread.

A spawned task with a class argument ran on LLVM and was rejected by QBE. Chronos will not pass scheduler/job class instances through spawned-task boundaries in portable code.

## Minimum Nox version

Not decided. Development currently uses Nox 2.1.0. A minimum supported version will be published only after compatibility tests.

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
