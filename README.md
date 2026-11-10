# Chronos

Chronos is a Nox-native scheduling library under development. Its planned MVP covers deterministic UTC scheduling, one-shot and interval triggers, a five-field UTC cron parser, and an application-owned in-process scheduler.

## Current status

Chronos is in Phase 1 (`0.1.0` development). The experimental typed time model, checked arithmetic, clock protocol, system clock, and fake clock are implemented. Scheduling triggers and cron are not implemented yet.

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

The current manifest entry demonstrates the real and fake clock implementations:

```sh
noxc check examples/clock.nox
noxc run examples/clock.nox
```

## Development

Work is tracked release by release in [todo.md](todo.md). Binding engineering rules are in [AGENTS.md](AGENTS.md).

The experimental public surface is listed in [docs/api.md](docs/api.md). Time and timezone decisions are documented in [docs/time-semantics.md](docs/time-semantics.md) and [docs/timezones.md](docs/timezones.md). The UTC cron contract is in [docs/cron.md](docs/cron.md), the portable execution boundary is in [docs/concurrency.md](docs/concurrency.md), and the threat model is in [docs/security.md](docs/security.md). Executed platform evidence is tracked in [docs/capabilities.md](docs/capabilities.md).

Do not infer support from a planned item. A feature is supported only after its implementation, deterministic tests, compiling example, and documentation are complete.

## License

Chronos is available under the [MIT License](LICENSE).
