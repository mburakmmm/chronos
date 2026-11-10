# Chronos

Chronos is a Nox-native scheduling library under development. Its planned MVP covers deterministic UTC scheduling, one-shot and interval triggers, a five-field UTC cron parser, and an application-owned in-process scheduler.

## Current status

Chronos is in Phase 0 (`0.0.x`): Nox platform verification and architecture proof-of-concept work. There is no public scheduling API yet.

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

The current manifest entry is a fixed-input calendar capability probe, not a Chronos scheduling example:

```sh
noxc check examples/calendar_probe.nox
noxc run examples/calendar_probe.nox
```

## Development

Work is tracked release by release in [todo.md](todo.md). Binding engineering rules are in [AGENTS.md](AGENTS.md).

The current time and timezone decisions are documented in [docs/time-semantics.md](docs/time-semantics.md) and [docs/timezones.md](docs/timezones.md). The UTC cron contract is in [docs/cron.md](docs/cron.md), the portable execution boundary is in [docs/concurrency.md](docs/concurrency.md), and the threat model is in [docs/security.md](docs/security.md). Executed platform evidence is tracked in [docs/capabilities.md](docs/capabilities.md).

Do not infer support from a planned item. A feature is supported only after its implementation, deterministic tests, compiling example, and documentation are complete.

## License

Chronos is available under the [MIT License](LICENSE).
