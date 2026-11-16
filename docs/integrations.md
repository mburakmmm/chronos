# Framework integrations

Status: experimental optional examples; core remains framework-independent.

Chronos exposes an application-owned manual scheduler. The framework examples attach one bounded `tick()` call to each incoming request and register terminal shutdown where the framework provides an application lifecycle hook. They do not add a hidden worker, timer, network endpoint, global scheduler, or mandatory dependency.

## Verified matrix

| Integration | Pinned release | Resolved commit | Nox | Evidence |
|---|---|---|---|---|
| Nyx | `v0.29.0` | `8acc737cadf58e5f7529e91e3838c095bce3c8ad` | `2.1.186` | LLVM/QBE code generation and execution |
| Aether | `v0.12.0` | `eef4664b5c7a2f9ec4c3bea19004f6bbebbdc001` | `2.1.186` | LLVM/QBE code generation and execution |

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

The first run requires network access to fetch the locked framework commits. The verifier requires Nox 2.1.186, checks that `noxc fetch` does not change either lock, and runs both examples on LLVM and QBE.

`NXL-007` still prevents one Chronos source tree from using the same package-qualified internal imports both as the root project and as a fetched dependency. The verifier therefore creates a temporary source-overlay project: it copies the real Chronos sources under `chronos/`, mechanically qualifies only their internal import statements, then compiles them with the locked framework package. This proves framework API compatibility, closure/codegen compatibility, and namespace isolation. It does **not** prove `noxc add chronos` consumption; Chronos remains source-checkout-only until `NXL-007` is resolved and a separate consumer test passes.

The examples are compiled and executed without starting a server or opening a socket. They validate the complete adapter functions through Nox code generation, not live HTTP timing or multi-worker behavior.
