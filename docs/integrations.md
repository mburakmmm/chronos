# Framework integrations

Status: experimental optional examples; core remains framework-independent.

Chronos exposes an application-owned manual scheduler. The framework examples attach one bounded `tick()` call to each incoming request and register terminal shutdown where the framework provides an application lifecycle hook. They do not add a hidden worker, timer, network endpoint, global scheduler, or mandatory dependency.

## Verified matrix

| Integration | Pinned release | Resolved commit | Nox | Evidence |
|---|---|---|---|---|
| Nyx | `v0.29.0` | `8acc737cadf58e5f7529e91e3838c095bce3c8ad` | `2.2.70` | LLVM/QBE code generation and execution |
| Aether | `v0.12.0` | `eef4664b5c7a2f9ec4c3bea19004f6bbebbdc001` | `2.2.70` | LLVM/QBE code generation and execution |

The manifests and exact locks live under `integrations/nyx/` and `integrations/aether/`. The root `nox.json` keeps an empty `requires` list, so neither framework becomes a Chronos core dependency.

## Nyx

`integrations/nyx/main.nox` provides:

- `build_scheduler()` — constructs and starts an explicitly owned `Scheduler` with `SystemClock`;
- `install_request_polling(application, engine)` — installs a Nyx `use_before` middleware that calls `tick()` once per request;
- an `nyx.app.on_shutdown` hook that stops the scheduler.

Call these from the same worker-local setup that creates the Nyx `Application`. Do not create one parent scheduler and assume Nyx workers share it.

## Aether

`integrations/aether/main.nox` provides the same ownership model through an Aether interceptor. `install_request_polling(application, engine)` obtains the application's `ModuleBuilder`, installs a before/after interceptor, and registers `engine.stop()` with `Application.on_shutdown`.

Call it from the worker-local Aether build path. The example deliberately does not register an administrative tick route.

## Request-driven semantics

These examples are integration adapters for applications that already receive requests frequently enough for best-effort maintenance work. Their semantics are intentionally narrow:

- no request means no `tick()`, so an idle server does not run jobs on time;
- an inline job runs inside the request path and can add response latency;
- one tick evaluates a bounded snapshot, but the handler itself is trusted application code and has no forceful timeout;
- one scheduler per framework worker creates independent schedules and can duplicate side effects if every worker registers the same logical job;
- there is no cross-worker coordination, persistence, leasing, or exactly-once guarantee.

Use a dedicated externally driven polling loop for deadlines that must progress while HTTP traffic is idle. Use idempotent handlers for side effects. Do not use the examples as a distributed scheduler.

## Verification shape and current package limitation

Run:

```sh
NOX_HOME=/tmp/chronos-integration-home python3 scripts/verify_integrations.py
```

The first run requires network access to fetch the locked framework commits. The verifier requires Nox 2.2.70, verifies the resolved revisions and runs both examples on LLVM and QBE.

The verifier commits unchanged working-tree Chronos modules to a temporary Git repository. Each consumer uses `noxc fetch` to load the resulting commit under the `chronos` alias. It exercises an independent cron and scheduler consumer and both framework consumers. A renamed dependency alias produces a duplicate `Clock` protocol on Nox 2.2.107 LLVM and QBE. Run `python3 scripts/reproduce_package_alias.py` with the installed compiler for the standalone reproduction. [NXL-007](../NOX_LIMITATIONS.md#nxl-007--a-package-cannot-use-one-internal-import-form-in-both-its-own-project-and-a-consumer)

The examples are compiled and executed without starting a server or opening a socket. They validate the complete adapter functions through Nox code generation, not live HTTP timing or multi-worker behavior.
