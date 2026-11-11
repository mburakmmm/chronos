# Execution policies

Status: experimental Phase 3 API for Nox 2.1.0 with partial scheduler integration.

The policy module validates bounded configuration and performs deterministic calculations without reading clocks or executing handlers. `JobPolicies` is accepted by the explicit `make_*_with_policies` job factories. The manual scheduler executes `skip`, `fire-once`, and bounded `catch-up`; it rejects queue-one and retry configurations atomically when a job is added.

Factories without the `_with_policies` suffix preserve source compatibility and install defaults: fire one late occurrence with the maximum supported grace, forbid overlap, and no retry. `Job.policy_config()` returns a defensive copy.

## Misfire

`skip_misfires(grace_period)`, `fire_once_misfires(grace_period)`, and `catch_up_misfires(grace_period, max_catch_up_count, max_evaluation_steps)` produce a `MisfirePolicy`.

Grace period is a nonnegative millisecond `Duration`. Its boundary is inclusive. Lateness greater than the grace period always resolves to `skip`. `fire-once` coalesces any positive available count into one dispatch. `catch-up` caps dispatches at 1,024 and evaluation work at 10,000 steps; the configured work bound must be at least the dispatch bound.

`dispatch_limit(available_occurrences, lateness)` and `evaluation_limit(available_occurrences)` are pure bounded decisions. They do not discover occurrences; trigger-specific scheduler integration remains responsible for doing so without moving cron or fixed-rate anchors.

An occurrence exactly equal to the observed clock is not a misfire and runs even under `skip`. For a late occurrence, the scheduler emits `misfired`, then either dispatches one occurrence under `fire-once` or emits `skipped`. Lateness beyond a fire-once grace period becomes skip. Skip calculates the next cron/fixed-rate occurrence strictly after the observed time without changing its anchor. A skipped fixed-delay occurrence schedules its next delay from the observed skip time because no handler completion exists.

Catch-up enumerates at most `max_evaluation_steps` planned occurrences from the existing trigger anchor and dispatches at most `max_catch_up_count`. Known excess occurrences are reported in one `coalesced` event. If the evaluation bound is reached while more occurrences remain due, `coalesced_truncated` is true and the count is a bounded known lower bound. The next schedule is calculated directly strictly after the tick's observed time, so uncounted backlog cannot create a storm.

Catch-up works for UTC one-shot/cron and monotonic delay/fixed-rate jobs. Completion-anchored fixed-delay rejects catch-up at registration because it has no sequence of missed planned occurrences without prior completions. Each catch-up execution still passes generation/enabled/schedule validation; removal or shutdown prevents later snapshot callbacks from starting.

## Overlap

`forbid_overlap()` allows one active run and retains no pending run. `queue_one_overlap()` still allows one active run but retains capacity for at most one pending occurrence.

The policy model deliberately rejects `allow`. Chronos currently has only an inline executor and has not verified shared scheduler state under concurrent callbacks. `max_concurrent_runs` is therefore one in every supported overlap configuration.

The current scheduler accepts only `forbid`; it rejects `queue-one` until pending-occurrence state is implemented and tested.

## Retry

`no_retry()` permits exactly one initial attempt. `fixed_retry(delay, max_attempts)` and `exponential_retry(base_delay, maximum_delay, max_attempts)` use 2–64 total attempts, including the initial execution. Retry delays must be positive.

`should_retry_after(completed_attempt)` answers whether another attempt is permitted. `delay_before_attempt(attempt)` uses attempt two for the first retry. Exponential delay doubles from the base and saturates at the configured maximum without overflowing signed 64-bit milliseconds.

Retries remain separate from recurrence. The scheduler currently accepts only `no-retry` and rejects fixed/exponential configurations. It does not yet decide how a delayed retry competes with the next regular occurrence, does not add jitter, and does not claim timeout or cancellation enforcement.

## Safety

All policy state is finite. There is no retry loop, catch-up loop, execution history, task spawning, or retained payload in this module. Side-effecting handlers will still require application-level idempotency; these policies cannot provide exactly-once effects.
