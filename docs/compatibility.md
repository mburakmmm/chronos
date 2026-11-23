# Compatibility

Status: Phase 5 core/store-contract and experimental SQLite adapter compatibility baseline.

Last verified locally: 2026-11-20

## Verified development target

| Component | Verified value | Evidence status |
|---|---|---|
| Nox compiler | `noxc 2.1.111` | verified locally and in cross-platform CI |
| Host | macOS 27.2 (`Darwin 27.2.0`) arm64 | verified locally |
| LLVM backend | Apple clang 21.0.0, arm64 target | full test/example matrix passed |
| QBE backend | Nox-installed QBE toolchain | full test/example matrix passed |
| Default profile | hosted | core, scheduler, examples, and `SystemClock` verified |
| Freestanding profile | no clock capability | 17 clock-independent modules type-checked on LLVM and QBE |

This table records a reproducible development baseline, not a promise that every earlier or later Nox release behaves identically. A minimum supported Nox version has not been selected. The complete cross-platform run is recorded in [GitHub Actions run 43460710827](https://github.com/mburakmmm/chronos/actions/runs/43460710827) for commit `a8211b0`.

## Backend matrix

| Verification | LLVM | QBE |
|---|---:|---:|
| Deterministic test programs | 21 passed | 21 passed |
| Public API contract | passed | passed |
| Executable examples | 16 passed | 16 passed |
| Shutdown regression | passed | passed |
| Task-local sleep probe | `fast sleeper` | `fast sleeper` |
| Class-valued command channel and bounded worker stop | output `7` | output `7` |
| Cooperative cancellation proof | output ends with `49995000` | output ends with `49995000` |
| Cross-module Internal-name import proof | output `7`, `9` | output `7`, `9` |
| Clock-independent freestanding modules | 17 checked | 17 checked |

The QBE backend is single-threaded and cooperative, while LLVM uses the documented multi-core scheduler. With Nox 2.1.111, `sleep_ms()` inside an async task suspends only the calling fiber on both tested backends. `Channel.wait(ms)` also provides a cooperative bounded wake primitive.

Cancellation remains cooperative: a task reaches cancellation at an await/checkpoint, but non-awaiting computation runs to completion. Chronos therefore does not claim forceful callback cancellation or enforceable in-process execution timeouts.

These primitives make a future background worker feasible, but Chronos currently supports only the application-driven manual scheduler. The product has not yet verified complete worker ownership, bounded command/response handling, or background scheduler lifecycle integration.

## Profile matrix

The following modules type-check with `--profile freestanding` on LLVM and QBE:

- `clock.nox`
- `cron.nox`
- `errors.nox`
- `events.nox`
- `executor.nox`
- `handler_registry.nox`
- `job.nox`
- `job_codec.nox`
- `persistent_scheduler.nox`
- `policy.nox`
- `registry.nox`
- `scheduler.nox`
- `store.nox`
- `stored_cron.nox`
- `stored_once.nox`
- `time.nox`
- `trigger.nox`

`system_clock.nox` type-checks in the hosted profile. Its freestanding rejection is expected and explicit: `nox.time.now_ms()` and `nox.time.boot_ms()` require the unavailable `clock` capability. Pure scheduling calculation remains usable without that adapter.

## Optional framework integration matrix

Framework packages currently require a newer compiler than the core baseline, so they run in an isolated job rather than changing Chronos's minimum-version claim.

| Integration | Framework pin | Compiler | Local macOS arm64 | CI Linux x64 |
|---|---|---|---|---|
| Nyx request polling | `v0.29.0` / `8acc737cadf58e5f7529e91e3838c095bce3c8ad` | Nox 2.1.186 | LLVM/QBE passed | LLVM/QBE passed |
| Aether request polling | `v0.12.0` / `eef4664b5c7a2f9ec4c3bea19004f6bbebbdc001` | Nox 2.1.186 | LLVM/QBE passed | LLVM/QBE passed |

The job verifies locked framework APIs through the source-overlay mechanism documented in `docs/integrations.md`. It is not external Chronos package-consumption evidence and makes no live-server, multi-worker, background-progress, or exactly-once claim.

## Optional SQLite adapter matrix

The data-only `store.nox` module is part of the pure cross-platform matrix and does not import a database driver. SQLite itself is checked separately so absence of a system SQLite library cannot turn persistence into a mandatory core dependency.

| Verification | Compiler | macOS arm64 | CI Linux x64 |
|---|---|---|---|
| File reopen, explicit commit/rollback, constraint recovery, prepared values | Nox 2.1.111 | LLVM/QBE passed | isolated CI job configured |
| `SQLiteJobStore` schema/create/load/update/delete/corruption/version integration | Nox 2.1.111 | LLVM/QBE passed | isolated CI job configured |
| Single-owner UTC one-shot process termination and reopen | Nox 2.1.111 | LLVM/QBE passed | isolated CI job configured |
| Single-owner UTC cron cursor process termination and reopen | Nox 2.1.111 | LLVM/QBE passed | isolated CI job configured |
| Persistent scheduler lifecycle, bounded outcomes and SQLite reopen | Nox 2.1.111 | LLVM/QBE passed | isolated CI job configured |

SQLite runtime evidence covers macOS arm64 and the isolated Linux x64 CI job. Power-loss recovery, concurrent schedulers, migration recovery and SQLite support on other targets require separate verification.

## Platform claims

| Platform | Status |
|---|---|
| Linux x64 | verified in GitHub Actions with the complete matrix above |
| Linux arm64 | verified in GitHub Actions with the complete matrix above |
| macOS arm64 | verified locally and in GitHub Actions with the complete matrix above |
| Windows x64 | verified in GitHub Actions with the complete matrix above |
| Other architectures | unverified; no support claim yet |
| Freestanding targets | pure/manual modules type-check; no hosted clock or runtime execution claim |

The CI workflow uses checksum-pinned Nox release archives on `ubuntu-24.04`, `ubuntu-24.04-arm`, `macos-15`, and `windows-latest`. Other architecture rows may move to verified only after real CI or recorded execution on those platforms. Documentation must not infer portability beyond the tested runner matrix.

## Reproduction commands

Use a writable isolated Nox home when the environment restricts the default compiler cache location.

```sh
NOX_HOME=/tmp/chronos-nox-home noxc test tests

for source in tests/*_test.nox; do
  NOX_HOME=/tmp/chronos-nox-home noxc run --backend qbe "$source" || exit 1
done

for backend in llvm qbe; do
  for source in examples/*.nox; do
    NOX_HOME=/tmp/chronos-nox-home noxc run --backend "$backend" "$source" || exit 1
  done
done
```

Freestanding checks must exclude `system_clock.nox` or expect its documented `CapabilityNotGranted` result.

Run the optional SQLite primitive and adapter integration matrix separately:

```sh
NOX_HOME=/tmp/chronos-persistence-nox-home python3 scripts/verify_persistence.py
```

## Compatibility policy

- Public behavior is tied to tests and compiling examples, not compiler documentation alone.
- Backend-specific differences are documented instead of silently skipped.
- A platform is not listed as verified without execution evidence.
- New Nox versions require the full test/example matrix plus the retained capability and limitation reproducers.
- Open and resolved compiler/runtime findings are tracked separately in `NOX_LIMITATIONS.md`.
- Nox does not enforce library visibility; only names allowlisted by `docs/api.md` carry a Chronos compatibility contract.
