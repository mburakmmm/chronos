<p align="center">
  <img src="docs/assets/chronos-banner.svg" alt="Chronos — deterministic scheduling for Nox" width="100%">
</p>

<p align="center">
  <a href="https://github.com/mburakmmm/chronos/actions/workflows/ci.yml"><img src="https://github.com/mburakmmm/chronos/actions/workflows/ci.yml/badge.svg" alt="Cross-platform CI"></a>
  <a href="https://github.com/mburakmmm/nox-lang/releases/tag/v2.1.111"><img src="https://img.shields.io/badge/Nox-2.1.111-0e7490" alt="Nox 2.1.111"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-f59e0b" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/status-experimental-64748b" alt="Experimental status">
</p>

Chronos is a Nox-native library for deterministic UTC scheduling, monotonic timers, five-field cron expressions, and bounded in-process job execution. It is designed for scripts, CLIs, services, and application-owned workers without requiring a database, daemon, web framework, or cloud service.

> [!IMPORTANT]
> Chronos is under active `0.x` development and has not published its first release. The API is experimental. Pin the resolved commit in `nox.lock` and review breaking changes before updating.

## Why Chronos

- **Correct time domains** — UTC wall-clock deadlines and monotonic elapsed delays are represented separately.
- **Deterministic scheduling** — pure trigger calculations and fake-clock tests avoid timing-dependent unit tests.
- **Bounded policies** — catch-up, overlap, retries, listeners, retained state, and parser work all have explicit limits.
- **Portable execution** — the supported baseline is an application-owned manual scheduler with an inline executor.
- **Honest guarantees** — no exactly-once, local-time cron, persistence, force-cancellation, or distributed coordination claims.

## Feature status

| Capability | Status | Notes |
|---|---|---|
| UTC one-shot scheduling | Implemented | Millisecond timestamps, explicit misfire handling |
| Monotonic delay and fixed-rate intervals | Implemented | Wall-clock jumps do not alter elapsed deadlines |
| Completion-anchored fixed-delay intervals | Implemented | Next run follows actual terminal completion |
| Five-field UTC cron | Implemented | Wildcards, lists, ranges, steps, bounded search |
| Manual in-process scheduler | Implemented | Explicit lifecycle, deterministic ordering, no hidden worker |
| Misfire and catch-up policies | Implemented | Skip, fire-once, and bounded catch-up |
| Overlap policies | Implemented | Forbid and one bounded pending occurrence |
| Retry policies | Implemented | None, fixed delay, and capped exponential backoff |
| Lifecycle events | Implemented | Synchronous bounded listeners with safe error categories |
| Nox package dependency consumption | Blocked | Nox 2.1.111 self-import limitation; see NXL-007 |
| Background scheduler | Deferred | Runtime primitives are proven; full worker ownership is not |
| IANA time zones and DST | Deferred | Current cron and calendar behavior is UTC-only |
| Persistence and distributed coordination | Deferred | No durable or exactly-once claim |

## Quick start

Install [Nox](https://noxlang.com/download/) 2.1.111:

```sh
curl -fsSL https://noxlang.com/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://noxlang.com/install.ps1 | iex
```

Clone and verify Chronos:

```sh
git clone https://github.com/mburakmmm/chronos.git
cd chronos
noxc test tests
noxc run examples/poll.nox
```

Chronos is currently verified from a source checkout. Nox 2.1.111 cannot yet resolve the same package-internal import form both from the package's own project root and from an external consumer. Dependency installation through `noxc add` is therefore not advertised until [NXL-007](NOX_LIMITATIONS.md) is resolved and consumer integration tests pass.

## UTC cron example

From a source checkout:

```nox
import nox.time
from cron import CronSchedule, parse
from time import UtcInstant

reference: UtcInstant = UtcInstant(
    nox.time.DateTime(2024, 1, 1, 8, 30, 0).to_epoch_ms()
)
weekdays: CronSchedule = parse("0 9 * * 1-5")
next_run: UtcInstant = weekdays.next_fire_after(reference)

print(nox.time.from_epoch_ms(next_run.as_epoch_ms()).to_str(), "UTC")
```

```text
2024-01-01 09:00:00 UTC
```

Runnable repository examples cover manual polling, one-shot jobs, intervals, UTC cron, cancellation, events, misfires, bounded catch-up, queue-one overlap, and fixed/exponential retries:

```sh
noxc run examples/once.nox
noxc run examples/every.nox
noxc run examples/cron_utc.nox
noxc run examples/misfire.nox
noxc run examples/catch_up.nox
noxc run examples/queue_one.nox
noxc run examples/retry.nox
noxc run examples/exponential_retry.nox
```

## Execution model

Chronos separates scheduling decisions from handler execution. Triggers are pure and never sleep, spawn tasks, or perform I/O. The scheduler is explicitly owned by the application:

1. Register jobs and start the scheduler.
2. Call `tick()` from the application's loop or worker.
3. Chronos evaluates a finite due snapshot and invokes trusted handlers inline.
4. Call `stop()` to enter terminal drain-current shutdown.

An active handler is allowed to return; shutdown starts no later due, catch-up, retry, or queued-overlap callback. Nox task cancellation is cooperative, so Chronos does not advertise forceful callback interruption or enforceable in-process execution timeouts.

## Time and policy defaults

- Calendar schedules and cron expressions are UTC-only.
- Cron uses `minute hour day-of-month month day-of-week` with Sunday `0`.
- Restricted day-of-month and day-of-week fields use traditional OR semantics.
- Recurring next-fire calculation is strictly after the reference.
- Default misfire behavior fires one late occurrence with maximum grace.
- Default overlap behavior forbids a second instance.
- Default retry behavior performs no retry.
- All schedules are in memory and are lost when the process exits.
- Side-effecting handlers should be idempotent; exactly-once execution is not provided.

## Verification

Every push and pull request runs the same release-quality matrix on GitHub-hosted runners:

| Runner | Architecture | Backends |
|---|---|---|
| Ubuntu | x64 | LLVM and QBE |
| Ubuntu | arm64 | LLVM and QBE |
| macOS | arm64 | LLVM and QBE |
| Windows | x64 | LLVM and QBE |

The matrix runs all deterministic tests, every executable example, concurrency proofs, and freestanding module checks with checksum-pinned Nox 2.1.111 release archives. The [first complete four-platform run](https://github.com/mburakmmm/chronos/actions/runs/43460710827) passed. See [compatibility](docs/compatibility.md) for dated evidence and [capabilities](docs/capabilities.md) for the underlying Nox API proofs.

Run the complete local matrix with:

```sh
python3 scripts/verify.py
```

## Documentation

| Topic | Document |
|---|---|
| Public API | [docs/api.md](docs/api.md) |
| Architecture decisions | [docs/architecture.md](docs/architecture.md) |
| Time semantics | [docs/time-semantics.md](docs/time-semantics.md) |
| UTC cron grammar | [docs/cron.md](docs/cron.md) |
| Scheduler lifecycle | [docs/scheduler.md](docs/scheduler.md) |
| Jobs and registry | [docs/jobs.md](docs/jobs.md) |
| Execution policies | [docs/policies.md](docs/policies.md) |
| Concurrency boundary | [docs/concurrency.md](docs/concurrency.md) |
| Security model | [docs/security.md](docs/security.md) |
| Platform compatibility | [docs/compatibility.md](docs/compatibility.md) |
| Nox limitations | [NOX_LIMITATIONS.md](NOX_LIMITATIONS.md) |
| Release roadmap | [todo.md](todo.md) |

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change. Bug reports and feature requests use structured GitHub issue forms; design questions belong in GitHub Discussions.

Jobs execute with the host process's authority. Only trusted application code should register handlers. Never place secrets in job names, metadata, event payloads, or serialized configuration. Report vulnerabilities through the process in [SECURITY.md](SECURITY.md).

## License

Chronos is released under the [MIT License](LICENSE).
