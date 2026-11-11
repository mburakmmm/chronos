# Lifecycle events

Status: experimental Phase 2 API for Nox 2.1.0.

Chronos exposes synchronous lifecycle observation without retaining an event history or creating a background worker. `Scheduler(clock, max_jobs, max_listeners=16)` accepts from zero through 64 listeners. Zero disables listener registration; attempting to exceed the configured capacity raises `EventListenerLimitError`.

## Event kinds

| Kind | Meaning | Planned time |
|---|---|---|
| `registered` | A job was accepted into the scheduler | absent |
| `scheduled` | A pending occurrence was assigned | present |
| `started` | Inline dispatch is beginning | present |
| `succeeded` | The handler returned normally | present |
| `failed` | The handler raised an exception | present |
| `misfired` | A planned occurrence was observed late | present |
| `skipped` | Misfire policy discarded the occurrence | present |
| `cancelled` | Scheduler ownership was removed | present only if a run remained pending |
| `scheduler-started` | Lifecycle entered `running` | absent |
| `scheduler-stopped` | Lifecycle entered `stopped` | absent |

Initial registration emits `registered` and, when a next occurrence exists, `scheduled`. Successful and failed recurring executions emit another `scheduled` event after their next time is calculated. A late occurrence emits `misfired`; policy rejection then emits `skipped` and, for a recurring job, the next `scheduled` event. Removing a completed job still emits `cancelled`, but without a pending planned time.

## Timestamp fields

`ChronosEvent` keeps planned and observed values separate:

- `time_domain` identifies `utc`, `monotonic`, or `none` for scheduler lifecycle events.
- `has_scheduled_time` controls whether `scheduled_time_ms` is meaningful. Its unit belongs to `time_domain`; UTC and monotonic integers must never be compared.
- `actual_start_utc_ms` and `actual_end_utc_ms` are wall-clock observations and may reflect a clock correction.
- `actual_start_monotonic_ms` and `actual_end_monotonic_ms` define the nonnegative `duration_ms`.
- `attempt` is one for current execution events and zero for non-execution events.
- `error_category` is empty except for `failed`, where the inline executor currently reports only `handler-error`.

The `started` snapshot is taken immediately before synchronous listener delivery and inline execution. Completion duration therefore measures the complete dispatch span from that snapshot through handler return, including time consumed by `started` listeners. It never derives elapsed duration from UTC wall time.

## Isolation and retention

Listeners run synchronously in registration order. Each listener call has its own exception boundary; a failure does not stop later listeners, corrupt scheduler lifecycle, or change the handler outcome. `listener_failure_count()` exposes a saturating aggregate count without retaining exception objects or messages.

There is no event queue, replay log, or retained payload buffer. Listener count is bounded, while delivered event objects are owned by the receiving application. Event delivery exposes job ID, time domain, planned/observed timestamps, attempt, duration, and a safe error category. It does not expose job name, metadata, handler arguments, handler results, or raw exception text.

Scheduler mutation, lifecycle transitions, and nested `tick()` calls from inside listener delivery are rejected and contained as listener failures. Read-only inspection remains available. Job handlers retain the separately documented generation-checked add/remove behavior.
