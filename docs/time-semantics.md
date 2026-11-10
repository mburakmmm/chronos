# Time semantics

Status: Phase 0 design record for Nox 2.1.0.

Chronos treats calendar deadlines, elapsed delays, and calendar field values as different concepts. Values are not converted between clock domains implicitly.

The implemented experimental types are `UtcInstant`, `MonotonicInstant`, and `Duration`. Checked arithmetic raises a Chronos error before Nox's wrapping `int` operations can overflow.

## UTC calendar time

Absolute deadlines and cron fire times use nonnegative Unix epoch milliseconds in UTC, from `0` (1970-01-01 00:00:00 UTC) through signed `int64` maximum.

- `nox.time.now_ms()` is the production wall-clock source.
- The wall clock can move forward or backward when the operating system clock changes.
- `nox.time.now()` and `nox.time.from_epoch_ms()` produce UTC `DateTime` values.
- A wall-clock jump changes when an absolute UTC deadline becomes due.
- Cron calculations operate on UTC calendar fields and never infer the machine's local timezone.
- Pre-1970 timestamps are rejected before Nox calendar conversion. The installed Nox 2.1.0 toolchain did not complete the tested negative-epoch conversion path, so Chronos does not advertise that range.

## Elapsed time and delays

Elapsed delays must not be represented as `now_ms() + delay`, because that makes them sensitive to wall-clock corrections.

Chronos uses a `Clock` protocol for UTC and monotonic readings. `SystemClock` backs its monotonic reading with `nox.time.boot_ms()`, while `FakeClock` exposes controlled UTC jumps and elapsed advancement for deterministic tests.

The intended delay rule is:

- Device suspend counts toward an `after(duration)` delay.
- If the delay expires while the device is suspended, the work becomes due on the first scheduler tick after resume.
- A wall-clock correction does not lengthen or shorten the delay.

This choice uses `boot_ms()` because Nox documents it as monotonic and suspend-inclusive across supported platforms. `Instant` remains useful for scoped measurements, but its device-suspend behavior differs between Linux/Android and Darwin platforms.

## `DateTime` validation

Nox 2.1.0 does not reject invalid constructor fields in the tested LLVM or QBE backend.

Observed examples:

```text
DateTime(2023, 2, 29, 0, 0, 0) -> to_str: 2023-02-29 00:00:00
                                      epoch: normalized to 2023-03-01
DateTime(2024, 13, 1, 0, 0, 0) -> accepted and normalized by epoch conversion
DateTime(2024, 1, 1, 24, 0, 0) -> accepted and normalized by epoch conversion
```

Chronos must validate year/month/day/hour/minute/second fields before constructing or accepting a calendar schedule. It must check leap years and the actual number of days in each month. Constructor success is not evidence that a date is valid.

## Integer arithmetic

The tested Nox `int` range is signed 64-bit. Plain `int` addition wraps on overflow in both LLVM and QBE; adding one to `9223372036854775807` produced `-9223372036854775808`.

Chronos therefore performs explicit precondition checks before timestamp or duration addition. A wrapped result must never be interpreted as a valid next fire time.

Negative durations are rejected. Zero-duration behavior is defined per trigger and cannot create a recurring trigger that repeatedly returns the same timestamp.

## Precision and exclusions

- Absolute and interval triggers preserve millisecond precision.
- The MVP cron dialect resolves to minute boundaries.
- Chronos makes no leap-second guarantee.
- Local civil time, UTC offsets, and IANA zone transitions are outside the MVP.
- Core trigger tests use a fake clock; real sleeps are limited to capability/integration probes.

## Clock capability profiles

Pure `from_epoch_ms()`/`DateTime.to_epoch_ms()` calendar conversion type-checks in Nox's freestanding profile.

Clock-reading and sleeping calls are rejected in the freestanding profile with `CapabilityNotGranted` for the `clock` capability. This includes `now_ms`, `boot_ms`, `instant_now`, `now`, `sleep_ms`, and `Instant` elapsed methods.
