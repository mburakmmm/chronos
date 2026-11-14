# Compatibility

Status: Phase 4 cross-platform compatibility baseline.

Last verified: 2026-11-14

## Verified development target

| Component | Verified value | Evidence status |
|---|---|---|
| Nox compiler | `noxc 2.1.111` | verified locally and in cross-platform CI |
| Host | macOS 27.2 (`Darwin 27.2.0`) arm64 | verified locally |
| LLVM backend | Apple clang 21.0.0, arm64 target | full test/example matrix passed |
| QBE backend | Nox-installed QBE toolchain | full test/example matrix passed |
| Default profile | hosted | core, scheduler, examples, and `SystemClock` verified |
| Freestanding profile | no clock capability | 11 clock-independent modules type-checked on LLVM and QBE |

This table records a reproducible development baseline, not a promise that every earlier or later Nox release behaves identically. A minimum supported Nox version has not been selected. The complete cross-platform run is recorded in [GitHub Actions run 43460710827](https://github.com/mburakmmm/chronos/actions/runs/43460710827) for commit `a8211b0`.

## Backend matrix

| Verification | LLVM | QBE |
|---|---:|---:|
| Deterministic test programs | 18 passed | 18 passed |
| Executable examples | 16 passed | 16 passed |
| Shutdown regression | passed | passed |
| Task-local sleep probe | `fast sleeper` | `fast sleeper` |
| Class-valued command channel and bounded worker stop | output `7` | output `7` |
| Cooperative cancellation proof | output ends with `49995000` | output ends with `49995000` |
| Clock-independent freestanding modules | 11 passed | 11 passed |

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
- `job.nox`
- `policy.nox`
- `registry.nox`
- `scheduler.nox`
- `time.nox`
- `trigger.nox`

`system_clock.nox` type-checks in the hosted profile. Its freestanding rejection is expected and explicit: `nox.time.now_ms()` and `nox.time.boot_ms()` require the unavailable `clock` capability. Pure scheduling calculation remains usable without that adapter.

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

## Compatibility policy

- Public behavior is tied to tests and compiling examples, not compiler documentation alone.
- Backend-specific differences are documented instead of silently skipped.
- A platform is not listed as verified without execution evidence.
- New Nox versions require the full test/example matrix plus the retained capability and limitation reproducers.
- Open and resolved compiler/runtime findings are tracked separately in `NOX_LIMITATIONS.md`.
