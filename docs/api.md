# Chronos public API

Status: experimental (`0.1.0` development).

Only APIs listed here are intended for public use. Leading-underscore functions and everything under `proofs/` are internal validation artifacts.

## `chronos.errors`

### `ChronosError`

Base class for Chronos-specific errors.

### `InvalidDurationError`

Raised when a duration or duration multiplier violates a nonnegative/positive duration contract.

### `TimeRangeError`

Raised before a timestamp or duration operation would overflow, underflow, reverse a monotonic interval, or construct an invalid monotonic value.

Callers should branch on the exception class, not message text.

## `chronos.time`

### `UtcInstant(epoch_ms)`

A signed 64-bit Unix epoch millisecond value. `as_epoch_ms()` returns the raw value.

### `MonotonicInstant(value_ms)`

A nonnegative monotonic counter value. It has no UTC meaning and cannot be converted to calendar time. `as_ms()` returns the counter value.

### `Duration(value_ms)`

A nonnegative elapsed duration in milliseconds. Negative input raises `InvalidDurationError`. `as_ms()` returns the raw duration.

### Arithmetic

- `add_duration(instant, duration) -> UtcInstant`
- `subtract_duration(instant, duration) -> UtcInstant`
- `add_monotonic_duration(instant, duration) -> MonotonicInstant`
- `elapsed_between(start, end) -> Duration`
- `multiply_duration(duration, factor) -> Duration`
- `require_positive_interval(duration) -> Duration`

All operations reject invalid input or overflow before Nox's wrapping integer arithmetic can occur.

`MIN_MS` and `MAX_MS` expose the supported signed 64-bit millisecond bounds.

## `chronos.clock`

### `Clock`

A structural protocol with:

- `now_utc() -> UtcInstant`
- `now_monotonic() -> MonotonicInstant`

### `FakeClock(utc_ms, monotonic_ms)`

A deterministic clock for tests and externally driven simulations.

- `advance(duration)` advances UTC and monotonic values atomically.
- `jump_utc_ms(delta_ms)` simulates a wall-clock correction without changing monotonic time.
- `set_utc_ms(utc_ms)` sets wall time without changing monotonic time.

Failed `advance` operations leave both values unchanged.

`chronos.clock` is pure and type-checks in Nox's freestanding profile.

## `chronos.system_clock`

### `SystemClock`

Production `Clock` implementation:

- UTC comes from `nox.time.now_ms()`.
- monotonic elapsed time comes from suspend-inclusive `nox.time.boot_ms()`.

This module requires Nox's hosted `clock` capability and is unavailable in the freestanding profile.

## `chronos.trigger`

Calendar and elapsed-time triggers use distinct protocols so UTC and monotonic values cannot be mixed.

### `UtcTrigger`

Structural protocol with `next_fire_after(reference: UtcInstant) -> UtcInstant | None`.

### `MonotonicTrigger`

Structural protocol with `next_fire_after(reference: MonotonicInstant) -> MonotonicInstant | None`.

Both contracts are strictly exclusive: every returned value is greater than the reference.

### `OnceTrigger(target)`

Returns its UTC target only when the target is strictly after the reference, otherwise `None`.

### `DelayTrigger(registered_at, delay)`

Calculates one monotonic deadline from registration time plus a nonnegative duration. It returns that deadline only while it remains strictly after the reference.

### `FixedRateTrigger(anchor, interval)`

Produces monotonic occurrences anchored to the original start. The interval must be greater than zero. The next occurrence is calculated mathematically without repeated addition, so callback duration and long gaps do not shift the anchor.

### `FixedDelay(delay)`

Stores a positive fixed-delay configuration. `next_after_completion(completed_at)` returns completion plus delay. Scheduler state owns the completion timestamp; fixed-delay is not treated as fixed-rate recurrence.

## Consumer imports

For a dependency aliased as `chronos`:

```nox-fragment
from chronos.clock import Clock, FakeClock
from chronos.system_clock import SystemClock
from chronos.time import Duration, MonotonicInstant, UtcInstant
from chronos.trigger import DelayTrigger, FixedDelay, FixedRateTrigger, OnceTrigger
```
