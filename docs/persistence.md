# Optional persistence

Status: Phase 5 contract and SQLite primitive proof; no production store adapter or durable-scheduling claim yet.

Chronos remains dependency-free and in-memory unless an application explicitly constructs a future persistence adapter. The current scheduler does not read or write a store. This first Phase 5 slice defines the data boundary that an adapter must implement and verifies the Nox/SQLite primitives required for the first adapter.

## Store boundary

`JobStore` is independent of `Scheduler`, callbacks, clocks, and executor state. It stores only `StoredJobDefinition` values:

- bounded job ID and human-readable name;
- trusted application handler key and bounded opaque handler configuration;
- trigger kind and bounded opaque trigger configuration;
- bounded opaque policy configuration;
- enabled state and UTC creation/update timestamps;
- positive compare-and-swap revision;
- explicit job-definition, handler-config, trigger, and policy format versions.

There is deliberately no handler closure, function pointer, connection, clock, live trigger object, retry deadline, running count, or pending callback in the record. A future hydration layer must resolve `handler_key` through an application-owned registry of trusted handlers. Stored text is data and must never be evaluated as Nox or shell code.

The three configuration strings are capped at 16,384 bytes each and reject embedded NUL so SQLite text binding cannot silently shorten a record. They are opaque at the store boundary so the persistence adapter does not invent serialization semantics. Chronos-owned codecs will be added alongside the trigger/policy types they support; applications must not assume arbitrary text is already a restorable Chronos schedule.

## Revision contract

Adapters implement optimistic compare-and-swap behavior:

- `put(definition, 0)` creates a missing record whose revision is `1`;
- `put(definition, N)` replaces only a record currently at `N`, and the replacement revision must be `N + 1`;
- `delete(job_id, N)` removes only a record currently at `N`;
- a missing, duplicate, stale, or skipped revision raises `StoreConflictError`;
- `load` and `load_all` return defensive definitions rather than mutable adapter-owned rows.

This prevents silent last-writer-wins updates inside one process. It is not a distributed lease, fencing token, or multi-process scheduler claim.

## Versioning and planned SQLite schema

The initial constants are schema version `1` and format version `1` for job definitions, handler configuration, trigger configuration, and policy configuration. The factory fills the supported format versions; direct construction is Internal and is used by adapters to reject unknown persisted versions explicitly.

The first SQLite adapter is planned around two tables:

- a singleton metadata row containing `schema_version`;
- a jobs table containing every `StoredJobDefinition` field with `job_id` as the primary key and `revision` as the compare-and-swap guard.

Schema creation and every future migration must run in one explicit `BEGIN IMMEDIATE` transaction. A store with a newer schema or record format must be refused, not guessed. Migration code, backup policy, and corrupted-row handling are not implemented in this slice.

## Verified Nox SQLite primitives

`proofs/persistence/sqlite_transaction_probe.nox` was executed with checksum-pinned Nox 2.1.111 on LLVM and QBE. It verifies:

1. opening a file-backed database and reopening it after close;
2. single-statement `BEGIN IMMEDIATE`, `COMMIT`, and `ROLLBACK` through `Connection.execute`;
3. zero-based `Statement.bind_*` parameter binding;
4. a constraint failure followed by explicit rollback of the entire transaction;
5. SQL-shaped handler text remaining data rather than executable SQL.

Nox exposes transaction control as SQL statements rather than a transaction object/context manager. Adapter code must therefore catch every operation error, issue `ROLLBACK`, and avoid swallowing a rollback failure. `Connection` objects are not safe to share between workers; the planned adapter is single-process and single-owner.

Run the retained proof with:

```sh
python3 scripts/verify_persistence.py
```

The proof is a capability check, not a durable-store integration test. It does not simulate process termination, disk-full behavior, torn writes, migration failure, or concurrent writers.

## Delivery and restart semantics still open

No current API promises at-most-once or at-least-once execution after restart. The scheduler is still ephemeral and ignores `JobStore`. Before a durable claim is added, the SQLite adapter and scheduler integration must define and test:

- the crash window before dispatch, after dispatch, and after handler side effects;
- restoration of UTC one-shot and UTC cron triggers;
- explicit restart semantics for monotonic delay, fixed-rate, and fixed-delay schedules;
- unknown handler keys, unsupported versions, and corrupted rows;
- atomic definition/state updates and migration recovery;
- bounded execution/error history, if any;
- application-level idempotency guidance.

Exactly-once side effects are not achievable merely by storing a row and will not be advertised.

## Security

- Database paths are trusted application configuration; Nox filesystem APIs do not confine untrusted paths.
- SQL values must use prepared bindings. Identifiers and schema SQL are fixed Chronos constants.
- Handler/configuration strings must not contain secrets. SQLite encryption is not provided by Chronos.
- Raw database payloads and SQLite error messages must not be copied into lifecycle events or safe error summaries.
- Unknown handler keys must fail closed; they must never select code dynamically or fall back to shell/process execution.
