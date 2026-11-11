# Execution policies

Status: experimental Phase 3 pure configuration API for Nox 2.1.0. Scheduler integration is not implemented yet.

The initial policy module validates bounded configuration and performs deterministic calculations without reading clocks, executing handlers, or mutating scheduler state. Its types are not yet accepted by `Job` or `Scheduler`; documentation below must not be read as an execution claim.

## Misfire

`skip_misfires(grace_period)`, `fire_once_misfires(grace_period)`, and `catch_up_misfires(grace_period, max_catch_up_count, max_evaluation_steps)` produce a `MisfirePolicy`.

Grace period is a nonnegative millisecond `Duration`. Its boundary is inclusive. Lateness greater than the grace period always resolves to `skip`. `fire-once` coalesces any positive available count into one dispatch. `catch-up` caps dispatches at 1,024 and evaluation work at 10,000 steps; the configured work bound must be at least the dispatch bound.

`dispatch_limit(available_occurrences, lateness)` and `evaluation_limit(available_occurrences)` are pure bounded decisions. They do not discover occurrences; trigger-specific scheduler integration remains responsible for doing so without moving cron or fixed-rate anchors.

## Overlap

`forbid_overlap()` allows one active run and retains no pending run. `queue_one_overlap()` still allows one active run but retains capacity for at most one pending occurrence.

The policy model deliberately rejects `allow`. Chronos currently has only an inline executor and has not verified shared scheduler state under concurrent callbacks. `max_concurrent_runs` is therefore one in every supported overlap configuration.

## Retry

`no_retry()` permits exactly one initial attempt. `fixed_retry(delay, max_attempts)` and `exponential_retry(base_delay, maximum_delay, max_attempts)` use 2–64 total attempts, including the initial execution. Retry delays must be positive.

`should_retry_after(completed_attempt)` answers whether another attempt is permitted. `delay_before_attempt(attempt)` uses attempt two for the first retry. Exponential delay doubles from the base and saturates at the configured maximum without overflowing signed 64-bit milliseconds.

Retries remain separate from recurrence. This pure slice does not decide how a delayed retry competes with the next regular occurrence, does not add jitter, and does not claim timeout or cancellation enforcement.

## Safety

All policy state is finite. There is no retry loop, catch-up loop, execution history, task spawning, or retained payload in this module. Side-effecting handlers will still require application-level idempotency; these policies cannot provide exactly-once effects.
