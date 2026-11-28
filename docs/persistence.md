# Optional persistence

Status: Phase 5 experimental single-owner SQLite store, UTC delivery and manual persistent scheduler.

The default `Scheduler` remains dependency-free and in-memory. Applications can opt into `PersistentScheduler` with an explicit `JobStore`. The SQLite adapter stores bounded definitions and delivery cursors. The scheduler and trusted handler registry manage execution.

## Store boundary

`JobStore` is independent of `Scheduler`, callbacks, clocks, and executor state. It stores only `StoredJobDefinition` values:

- bounded job ID and human-readable name;
- trusted application handler key and bounded opaque handler configuration;
- trigger kind and bounded opaque trigger configuration;
- bounded opaque policy configuration;
- enabled state and UTC creation/update timestamps;
- positive compare-and-swap revision;
- explicit job-definition, handler-config, trigger, and policy format versions.

Persisted records contain no executable values or live scheduler state. Stored text is data and must never be evaluated as Nox or shell code.

The three configuration strings are capped at 16,384 bytes each and reject embedded NUL. They are opaque at the database boundary. The UTC job codec applies additional format and policy validation.

## Handler binding

The application registers trusted callbacks in its own `HandlerRegistry`. Binding a loaded record validates it and returns a scheduler-compatible callback capturing the stored handler configuration. An absent key raises `UnknownHandlerError`. The registered function runs only when the returned callback is invoked.

## UTC definition codec

The version 1 Chronos codec supports two trigger kinds. `once-utc` stores one canonical unsigned decimal UTC epoch millisecond value. `cron-utc` stores the original five-field UTC expression, retaining its wildcard syntax and using the existing cron parser. Both are encoded using the functions in `job_codec`.

The version 1 policy configuration has nine pipe-delimited fields in order. The format is bounded at 128 bytes. Numeric fields use canonical unsigned decimal within signed 64-bit range. Policy constructors enforce individual limits, and the codec checks combinations such as retry with catch-up.

```text
misfire-kind|grace-ms|catch-up-count|evaluation-steps|overlap-kind|retry-kind|max-attempts|base-delay-ms|max-delay-ms
```

`restore_utc_job` creates one in-memory job using the decoded schedule and policies and a trusted handler. It preserves enabled state and both UTC timestamps. Execution history, arguments beyond handler configuration, metadata and process-local monotonic schedules are outside this format. Existing opaque application records remain readable through `JobStore`. To restore older opaque values as jobs, explicitly translate them using the codec before updating their stored revision.

The runnable SQLite example restores a one-shot job before registering it with the manual scheduler. At registration the scheduler calculates eligibility from its current clock. Restart reconciliation, past occurrences and prior execution state require a separately defined delivery contract.

## Revision contract

Adapters implement optimistic compare-and-swap behavior:

- `put(definition, 0)` creates a missing record whose revision is `1`;
- `put(definition, N)` replaces only a record currently at `N`, and the replacement revision must be `N + 1`;
- `delete(job_id, N)` removes only a record currently at `N`;
- a missing, duplicate, stale, or skipped revision raises `StoreConflictError`;
- `load` and `load_all` return defensive definitions rather than mutable adapter-owned rows.

This prevents silent last-writer-wins updates inside one process. It is not a distributed lease, fencing token, or multi-process scheduler claim.

## SQLite adapter

`open_sqlite_store(path)` opens or creates a file-backed database and returns a `SQLiteJobStore`. The path is trusted application configuration. The application must keep one owner for the connection, must not share it between Nox workers, and must call `close()`. Close is idempotent; later operations fail explicitly.

The adapter uses three fixed-schema tables:

- `chronos_metadata`, containing one schema-version row;
- `chronos_jobs`, containing every `StoredJobDefinition` field with `job_id` as primary key and `revision` as the compare-and-swap guard;
- `chronos_outcomes`, holding one optional delivery status per job.

A store accepts up to 10,000 definitions. A fresh create at capacity raises `StoreError`. Listing rejects an over-capacity database. SQLite validates text storage type, byte length and embedded NUL before values cross the Nox driver boundary. See `NXL-009` in the limitations ledger.

Run the definition-only example with `noxc run examples/persistence/sqlite_definitions.nox`. It uses an in-memory SQLite database so it can run without leaving a file.

Every value is bound through a prepared statement. Table names, columns, and DDL are fixed Chronos constants. `load_all()` orders rows by job ID for deterministic inspection. Persisted rows are decoded and validated as untrusted data; invalid values raise `StoreCorruptionError`, while newer schema or record versions raise `UnsupportedStoreVersionError`. Raw SQLite diagnostics and row contents are replaced by a fixed `StoreError` message.

The adapter is single-process/single-owner in this release. Conditional SQL makes revision checks atomic even if another database connection writes the same file, but that is not permission to share one scheduler across processes and does not establish job ownership, leases, fencing, or distributed execution.

## Versioning and schema initialization

The current database schema version is `2`. Job definition, handler, trigger and policy formats stay at version `1`. The factory fills the supported format versions and adapters reject unknown versions explicitly.

Initialization and v1-to-v2 migration run in one explicit `BEGIN IMMEDIATE` transaction. Migration creates an empty outcome table and updates the schema marker while preserving jobs, revisions and delivery cursors. Failure rolls back and closes the connection. Versions beyond the supported schema or record formats are refused. Version 1 binaries cannot open a migrated file.

## Verified Nox SQLite primitives

`proofs/persistence/sqlite_transaction_probe.nox` and `proofs/persistence/sqlite_store_integration.nox` run with checksum-pinned Nox 2.2.70 on LLVM and QBE. Together they verify:

1. opening a file-backed database and reopening it after close;
2. single-statement `BEGIN IMMEDIATE`, `COMMIT`, and `ROLLBACK` through `Connection.execute`;
3. zero-based `Statement.bind_*` parameter binding;
4. a constraint failure followed by explicit rollback of the entire transaction;
5. SQL-shaped handler text remaining data rather than executable SQL;
6. create, reopen/load, conditional update, stale-write conflict, and conditional delete;
7. persisted handler key/configuration records with no callback serialization;
8. rejection of newer schema/trigger versions and malformed persisted definitions;
9. fixed safe messages for backend errors and explicit closed-store behavior.

Nox exposes transaction control as SQL statements rather than a transaction object/context manager. Initialization therefore owns an explicit rollback path. `Connection` objects are not safe to share between workers; the adapter is single-owner.

Run the retained proof with:

```sh
python3 scripts/verify_persistence.py
```

The definition-store tests cover the database operations above. A separate subprocess suite covers one-shot delivery across process termination.

## Atomicity, crash windows, and restart boundary

Each create, update, and delete is one SQLite statement in autocommit mode. Create uses a primary-key conflict guard; update and delete include the expected revision in their `WHERE` clause. The adapter reports success only after `Statement.execute()` returns. A reopened store observes committed definitions, as covered by the integration test.

SQLite owns journaling, synchronization, filesystem, and power-loss behavior; Chronos does not change durability pragmas. If a process fails before a mutation commits, the previous committed definition remains. If it fails after SQLite commits, the replacement may be present even when the application did not observe the return value. The caller must reload and compare revisions after an ambiguous failure instead of blindly replaying a write. This is definition atomicity, not execution atomicity.

The definition row omits monotonic instants, running counts, retry deadlines, pending overlap state and callbacks. Reopening recovers the stored records. The application owns startup and elapsed-time scheduling.

## At-most-once UTC one-shot dispatch

Applications can call `dispatch_stored_once` from their own polling loop with an explicit UTC reading. A future target stays enabled. A due target is validated and its policy evaluated. A single committed compare-and-swap advances the revision and sets `enabled = false` before any callback runs. The SQLite connection must stay in autocommit mode. The callback receives the original planned UTC timestamp and attempt `1`. A misfire skip also consumes the record. The callback runs synchronously.

An existing disabled definition returns `disabled`, whether it was consumed or disabled by the application. Inspect an explicitly recorded outcome with `load_outcome`. Explicitly enabling the definition again or deleting and recreating it arms a new delivery. Keep one application owner and one dispatch path per armed job.

If the process terminates before commit, an enabled record remains eligible under its misfire policy. If the commit succeeds and the process terminates before the callback starts, the next poll sees a disabled record and the callback is lost. After a callback starts, the next poll also sees a disabled record, whether the callback ran to completion, raised or performed only some of its side effects. The result returned by the function is transient. Use application-level idempotency for manual rearming and side effects.

The verified SQLite suite reopens the same database in a fresh process after termination before the write, before transaction commit, after commit, and after a handler side effect. It also checks pending polls, misfire skip and a redacted handler failure. These tests establish process-restart behavior for a single owner. Power loss, disk failure, migration recovery and other backends require separate verification.

Run the in-memory example with `noxc run examples/persistence/dispatch_once.nox`. Use a file-backed SQLite store for process-restart behavior.

## At-most-once UTC cron dispatch

Persistent cron uses trigger kind `cron-cursor-utc` in format version 1. The configuration is `next-epoch-ms|expression`. The first field uses the same canonical decimal format as `once-utc` and must be a match for the bounded five-field UTC expression. `encode_stored_cron(expression, start)` initializes it at the first match at or after the application's chosen start. Earlier `cron-utc` definitions remain available for in-memory restoration. To opt into persistent delivery, explicitly choose a start and update the stored kind and configuration through a revision-checked write.

Each poll considers the first outstanding occurrence. If it is due, `fire-once` invokes that occurrence within its grace window. `skip` drops late occurrences. An occurrence exactly at its due time is eligible, and the grace window is measured from the persisted occurrence. For either decision, one committed write advances the cursor to the first matching time strictly after the observed clock. Intermediate due occurrences are coalesced and do not each invoke a callback, even if the poll lands exactly on a later match. Retry and catch-up policies are rejected. A backward wall-clock jump leaves the cursor intact, so consumed times stay consumed.

The application polls using the same single-owner, autocommit SQLite constraints as for one-shot delivery. An exit before commit leaves the original cursor. An exit after commit preserves the advance and can lose the current invocation. Each later occurrence remains eligible by its own policy. Keep the same cursor as a schedule is disabled and re-enabled unless intentionally setting a new start. Search exhaustion or write failure propagates before callback invocation with the stored cursor unchanged by the poll's own write when the failure precedes commit.

Process tests verify rollback before commit, restart after commit, exit after a handler effect, misfire skip, rejection of a malformed cursor and the first subsequent on-time occurrence. Run the companion example with `noxc run examples/persistence/dispatch_cron.nox`.

## Persistent scheduler lifecycle

Construct `PersistentScheduler` with an open store, a trusted handler registry, a clock and a watch limit. The application supplies the IDs to watch, then calls `start()` and drives `tick()` on a single owner. A tick reads the current definition of each watched ID in registration order. It handles `once-utc` and `cron-cursor-utc` records, plus `cron-cursor-zoned` when an explicit provider is configured. Application startup must rebuild watches and handler registrations after reopening the database. Zoned records also require the pinned provider. [Zoned dispatch and restart](timezone-design.md#stored-zoned-dispatch)

Poll results contain only the job ID and a fixed status. Per-job faults leave the remaining watches eligible for the same poll. The scheduler stores at most one safe outcome per watch in memory. No-op statuses such as pending leave that outcome intact. Unwatch releases the outcome. Reopening the store retains consumed one-shots and cron cursors. A fresh scheduler has an empty outcome cache.

Call `stop()` before closing the store. If a callback requests stop, it can finish and the tick stops before checking another job. Recursive ticks and watch changes during a tick are rejected. The application controls the poll cadence. Callbacks and store access are synchronous.

Run the example with `noxc run examples/persistence/poll_stored.nox`.

## Optional durable outcomes

After a tick, the application can record terminal results with `record_outcome(result.job_id, result.committed_revision, result.status)` on the same SQLite store. Pass only results with a positive committed revision from the active job lifetime. Discard in-flight results before deleting and recreating an ID, since revisions belong to a single job lifetime. The status allowlist is `succeeded`, `handler-failed` and `skipped`. The application remains responsible for recording or discarding results.

SQLite retains at most one row per job and accepts only the first write for a current revision. A change of revision hides the previous outcome. The next recorded result replaces the row. Deleting a job also deletes its outcome. The stored fields are job ID, revision and fixed status. Handler payloads, configuration and exception messages stay out of the outcome table.

Recording happens after delivery and uses a separate commit. A process exit after cursor advancement, after execution or before outcome recording may leave no visible outcome. This is an unknown result, and the committed cursor still governs restart eligibility. A missing outcome cannot establish whether a callback started or completed.

## Remaining delivery work

- explicit restart semantics for monotonic delay, fixed-rate, and fixed-delay schedules;
- execution-state updates and migration recovery;
- bounded execution/error history, if any;
- application-level idempotency guidance.

Exactly-once side effects are not achievable merely by storing a row and will not be advertised.

## Runtime credentials

Store public account or credential aliases in job definitions. Register a trusted callback that maps each allowed alias to an application-owned credential source at execution time. The callback can read process-injected configuration or ask an application-managed secret provider. Validate the alias against the application's allowlist before asking for a credential. A missing credential can raise a handler error and follows the job's delivery policy.

The [credential example](../examples/persistence/secret_reference.nox) accepts a fresh SQLite path as its first program argument. It stores the public alias `reporting` and reads `CHRONOS_EXAMPLE_REPORT_TOKEN` only inside the registered handler. It prints the fixed delivery status. The persistence verifier supplies a synthetic credential and checks the process output, reopened rows and fixture file bytes. It also covers absent and empty credentials.

Chronos treats caller-supplied configuration as opaque text. The application must keep credentials out of all stored fields and callback logs. Use public aliases without embedding secret values in identifiers, database paths or command-line arguments. Protect the SQLite file and its backups according to the sensitivity of the remaining application data.

## Security

- Database paths are trusted application configuration; Nox filesystem APIs do not confine untrusted paths.
- SQL values must use prepared bindings. Identifiers and schema SQL are fixed Chronos constants.
- Handler/configuration strings must not contain secrets. SQLite encryption is not provided by Chronos.
- Raw database payloads and SQLite error messages must not be copied into lifecycle events or safe error summaries.
- Unknown handler keys must fail closed; they must never select code dynamically or fall back to shell/process execution.
