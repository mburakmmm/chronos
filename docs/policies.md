# Execution policies

Status: experimental Phase 3 API; latest matrix uses Nox 2.1.111.

The policy module validates bounded configuration and performs deterministic calculations without reading clocks or executing handlers. `JobPolicies` is accepted by the explicit `make_*_with_policies` job factories. The manual scheduler executes `skip`, `fire-once`, bounded `catch-up`, `forbid`, bounded `queue-one`, fixed-delay retry, and capped exponential retry.

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

The inline scheduler accepts both modes. While a callback is active, a reentrant `tick()` evaluates only that active job for overlap and defers unrelated callbacks to the outer tick. `queue-one` retains the earliest next planned occurrence in one scalar slot; another observed overlapping occurrence is discarded. `forbid` retains none. These decisions emit `overlap-queued` or `overlap-skipped` and update separate tick counters without incrementing job execution count.

One-shot UTC and delay jobs have no second occurrence to overlap. Fixed-delay recurrence is completion-anchored, so it also has no next occurrence before the active callback returns. Fixed-rate and UTC cron can expose a next planned occurrence during a reentrant tick. Removal cancels the one pending slot; disable followed by enable clears it and recalculates from the current clock.

This is bounded single-thread reentrancy behavior, not thread safety. The scheduler still rejects concurrent `allow`, spawns no tasks, and never invokes two callbacks simultaneously.

## Retry

`no_retry()` permits exactly one initial attempt. `fixed_retry(delay, max_attempts)` and `exponential_retry(base_delay, maximum_delay, max_attempts)` use 2–64 total attempts, including the initial execution. Retry delays must be positive.

`should_retry_after(completed_attempt)` answers whether another attempt is permitted. `delay_before_attempt(attempt)` uses attempt two for the first retry. Exponential delay doubles from the base and saturates at the configured maximum without overflowing signed 64-bit milliseconds.

Retries remain separate from recurrence. The scheduler accepts `no-retry`, `fixed_retry`, and `exponential_retry`. A retry delay is elapsed time measured only by the monotonic clock. Attempt one is the original dispatch and attempts two through `max_attempts` reuse the original occurrence's planned timestamp and time domain. Exponential attempt two uses the base delay, later attempts double it, and every result saturates at `maximum_delay`.

While a retry chain is pending, the job's regular recurrence is suspended. The retry wins over any intervening cron, fixed-rate, or fixed-delay occurrence. On success or exhaustion, one-shot completes; fixed-rate and cron query their unchanged trigger anchor strictly after terminal completion; fixed-delay starts its normal delay from terminal monotonic completion. A late retry dispatches once and does not enter misfire/catch-up logic.

Retry is currently incompatible with `catch-up` and `queue-one`; registration rejects both combinations atomically for fixed and exponential policies. Removal cancels a pending retry. Disable suspends it, while re-enable discards it and recomputes the regular trigger. Stop during a failing callback does not create a new retry. Retry-deadline overflow changes the scheduler to `failed` rather than wrapping the monotonic integer.

Only contained handler failures (`handler-error`) are retryable. Invalid schedules fail before handler dispatch, scheduler/infrastructure failures are not retried, and cancellation never manufactures another attempt. There is no jitter, timeout, task cancellation, or exactly-once claim.

## Safety

All policy state is finite. The scheduler retains one retry deadline, upcoming attempt number, and original planned time per retrying job; it retains no retry list or execution history. Side-effecting handlers require application-level idempotency because any attempt may have produced effects before raising, and these policies cannot provide exactly-once effects.
