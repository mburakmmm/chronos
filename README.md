# Chronos

Chronos is a Nox-native scheduling library under development. Its planned MVP covers deterministic UTC scheduling, one-shot and interval triggers, a five-field UTC cron parser, and an application-owned in-process scheduler.

## Current status

Chronos Phase 1 (`0.1.0`) and Phase 2 (`0.2.0`) implementation work is complete but unreleased. Phase 3 (`0.3.0`) is in development. The application-driven manual scheduler supports UTC one-shot/cron, monotonic delay/fixed-rate, completion-anchored fixed-delay jobs, bounded synchronous lifecycle listeners, bounded `skip`/`fire-once`/`catch-up` misfire handling, a single pending `queue-one` overlap in the inline/reentrant execution model, and bounded fixed-delay handler retries. Exponential retry execution remains gated.

The currently verified development compiler is Nox 2.1.0 on macOS arm64. This is not yet a support commitment; backend and platform claims will be added only after executable tests.

## Design boundaries

- UTC calendar timestamps and monotonic elapsed time have separate semantics.
- The MVP cron dialect will be five-field and UTC-only.
- Trigger calculation will remain separate from callback execution.
- The portable baseline will be a manual-tick scheduler with an inline executor.
- Schedules will be in-memory and will not survive process exit.
- Chronos will not claim exactly-once execution.
- Time zones, persistence, background execution, and distributed coordination are deferred until their prerequisites are verified.
- The core will not depend on Nyx, Aether, Aura, Feather, Nova, Rune, or Noxen.

## Repository layout

Nox package modules intended for consumers will live at the repository root. This allows a dependency aliased as `chronos` to expose modules such as `chronos.cron`. The decision and its compiling proof are recorded in [docs/architecture.md](docs/architecture.md).

The current manifest entry demonstrates manual polling with an injected fake clock:

```sh
noxc check examples/poll.nox
noxc run examples/poll.nox
```

Clock, trigger, and UTC cron calculations are demonstrated separately:

```sh
noxc run examples/clock.nox
noxc run examples/triggers.nox
noxc run examples/cron_utc.nox
noxc run examples/registry.nox
noxc run examples/once.nox
noxc run examples/every.nox
noxc run examples/cancel.nox
noxc run examples/events.nox
noxc run examples/policies.nox
noxc run examples/misfire.nox
noxc run examples/catch_up.nox
noxc run examples/queue_one.nox
noxc run examples/retry.nox
```

## Development

Work is tracked release by release in [todo.md](todo.md). Binding engineering rules are in [AGENTS.md](AGENTS.md). Nox compiler/runtime issues encountered during implementation are maintained separately in [NOX_LIMITATIONS.md](NOX_LIMITATIONS.md).

The experimental public surface is listed in [docs/api.md](docs/api.md). Job and registry contracts are in [docs/jobs.md](docs/jobs.md), manual scheduler behavior is in [docs/scheduler.md](docs/scheduler.md), lifecycle observation is in [docs/events.md](docs/events.md), and pure policy configuration is in [docs/policies.md](docs/policies.md). Time and timezone decisions are documented in [docs/time-semantics.md](docs/time-semantics.md) and [docs/timezones.md](docs/timezones.md). The UTC cron contract is in [docs/cron.md](docs/cron.md), the portable execution boundary is in [docs/concurrency.md](docs/concurrency.md), and the threat model is in [docs/security.md](docs/security.md). Executed platform evidence is tracked in [docs/capabilities.md](docs/capabilities.md).

Do not infer support from a planned item. A feature is supported only after its implementation, deterministic tests, compiling example, and documentation are complete.

## License

Chronos is available under the [MIT License](LICENSE).
