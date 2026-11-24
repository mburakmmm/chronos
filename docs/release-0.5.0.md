# Chronos 0.5.0 release draft

Status: draft for a GitHub source release. The working manifest remains `0.5.0-dev` pending approval.

## Highlights

- Optional single-owner SQLite storage with revision-checked writes, v1-to-v2 schema migration, and bounded outcome retention.
- Manual `PersistentScheduler` for watched UTC one-shot and cron definitions. The in-memory scheduler remains the default.
- At-most-once callback starts across process restart for the verified SQLite delivery paths. Chronos commits consumption or cursor advancement before invoking a callback. An interruption after that commit can lose the invocation. Optional outcomes use a separate commit and can be absent after a crash.
- Runtime credential lookup through trusted application handlers. Keep secrets out of persisted fields and store public aliases instead.

## Upgrade notes

Opening a v1 SQLite database upgrades it to v2 transactionally. Job definitions and delivery cursors are preserved, and the outcome table starts empty. Keep a copy of the v1 file if retaining the option to run an older binary. See the [migration guide](migration-guide.md) and [persistence rules](persistence.md).

The public API remains experimental. Use the source checkout. External Nox package-consumer imports are blocked by NXL-007, so Nox registry availability is outside this release draft. See [known Nox limitations](../NOX_LIMITATIONS.md).

## Verification

The development snapshot `24f970d` passed [all six CI jobs](https://github.com/mburakmmm/chronos/actions/runs/45267286106). Nox 2.1.111 verified the core on LLVM and QBE across Linux x64, Linux arm64, macOS arm64 and Windows x64. Hosted SQLite was verified on macOS arm64 locally and Linux x64 in CI. The separate Linux x64 framework job used Nox 2.1.186.

Reproduce the core and SQLite checks with the pinned Nox compiler on your path:

```sh
python3 scripts/verify.py
python3 scripts/verify_persistence.py
```

SQLite delivery evidence covers a single owner and process restart. Power-loss recovery, shared execution, exactly-once side effects and persistent monotonic schedules are outside this scope.

## Publication

After explicit approval, set the manifest to `0.5.0`, date the changelog entry, and verify CI on the final release commit. Use that verified commit for the `v0.5.0` tag and GitHub Release.
