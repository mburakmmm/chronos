# Jobs and registry

Status: implemented experimental Phase 2 foundation for Nox 2.1.0.

## Job identity and construction

Jobs are created with `make_utc_job`, `make_monotonic_job`, or `make_fixed_delay_job`. The factories keep wall-clock/calendar triggers separate from elapsed-time triggers while exposing a shared `Job` view to registries and executors.

The companion `make_utc_job_with_policies`, `make_monotonic_job_with_policies`, and `make_fixed_delay_job_with_policies` factories require an explicit `JobPolicies`. The original factories install fire-once/max-grace, forbid-overlap, and no-retry defaults. Construction and `policy_config()` both make defensive copies so later mutation of the supplied or returned configuration does not alter the stored job policy.

Job IDs are stable scheduling identities. They are bounded to 128 ASCII bytes and accept letters, digits, `.`, `-`, `_`, and `:`. Names are nonempty and bounded to 256 UTF-8 bytes. Changing `job_id` after registration is unsupported; the registry snapshots the key and reports `InvalidJobError` if mutation is detected.

Duplicate IDs raise `DuplicateJobError`. There is no implicit replacement.

## Handlers and contexts

A handler is a verified Nox function value with type `(JobContext) -> None`. Captured closures compile and run on the tested LLVM and QBE backends.

`JobContext` records:

- the stable job ID;
- an explicit `utc` or `monotonic` time domain;
- the planned timestamp in milliseconds within that domain;
- a positive attempt number.

The time domain is never inferred from the integer. Scheduler code must construct the context from the matching trigger domain.

Retry attempts preserve the original occurrence's planned timestamp and domain while incrementing `attempt`. Total execution count counts every callback attempt; the bounded latest outcome replaces the preceding attempt summary and no per-attempt history is retained.

Fixed-delay jobs are a distinct subtype rather than a pure monotonic trigger. Their first deadline is registration plus delay; every later deadline is actual monotonic completion plus delay. An overdue first deadline coalesces into one execution at the observed monotonic time rather than a catch-up loop. Without retry, success or handler failure is terminal for that occurrence. With fixed retry, the regular delay begins only after terminal success or attempt exhaustion. Removing the job prevents future runs but cannot interrupt the active inline callback.

Handlers are trusted in-process application code. Chronos does not serialize a closure or function pointer, evaluate strings, or reconstruct executable code. A future persistent definition will store a handler key and require the application to register its trusted implementation.

## Bounded metadata and outcome state

A job accepts at most 16 metadata entries. Keys are unique bounded identifiers of at most 64 bytes; values are at most 256 bytes. Construction makes a defensive copy so later mutation of the input list or entries cannot change stored metadata.

Metadata is not a secret store. Applications must not put credentials, tokens, or private payloads in it.

Chronos retains no result object and no execution history in the job. The current bounded summary contains only:

- total execution count;
- `never`, `succeeded`, or `failed` status;
- a safe error category of at most 64 identifier bytes;
- the latest completion UTC timestamp when present.

Raw exception text is intentionally not retained.

## Registry behavior

`JobRegistry` is an application-owned in-memory object with an explicit capacity from 1 through 10,000 jobs. It uses lexical job-ID order, so inspection order is deterministic and independent of insertion order.

The registry supports add, find/get, list, enable, disable, remove, contains, and count. Missing required targets raise `JobNotFoundError`.

`remove` cancels only future ownership of the schedule. It does not claim to interrupt a handler that is already running. The standalone registry allows the ID to be added again after removal because it does not execute jobs. The manual scheduler adds an active-run guard and rejects reuse until the inline callback has returned.

All registry state is process memory. Process exit loses it. No persistence, cross-process visibility, thread safety, or exactly-once behavior is implied.
