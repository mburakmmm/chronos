# Benchmarks

Status: Phase 4 measurement infrastructure. Benchmark timings are observations, not API guarantees or CI pass/fail thresholds.

## Scope

The suite measures:

- parsing one bounded, nontrivial five-field UTC cron expression;
- dense (`*/5`) and sparse (February 29) next-fire calculation;
- scheduler due collection with 100, 1,000, and 10,000 jobs;
- no due jobs, one due job, and all jobs due at the same timestamp;
- raw `sleep_ms` wake overshoot;
- fixed-rate planned-anchor drift and observed handler-start lateness;
- handler-local and Chronos event-observed callback duration.

`due_lookup_benchmark.nox` calls the scheduler's internal `_collect_due` operation. Its setup directly constructs valid registry and schedule entries so public registration cost, callback execution, event delivery, and rescheduling do not contaminate the due-collection measurement. This is benchmark-only access and does not make `_collect_due`, `RegisteredJob`, `ScheduledEntry`, or `DueItem` public API.

The benchmark retains result checksums so the measured work remains observable. Chronos uses Nox's monotonic `Instant.elapsed_ms()` for timing. Each benchmark is an ahead-of-time compiled process, so no JIT warm-up policy is implied.

## Running

Run both verified backends from the repository root:

```sh
python3 scripts/run_benchmarks.py
python3 scripts/run_timing_benchmarks.py
```

Select an exact compiler without changing the installed Nox toolchain:

```sh
NOXC=/absolute/path/to/noxc python3 scripts/run_benchmarks.py
NOXC=/absolute/path/to/noxc python3 scripts/run_timing_benchmarks.py
```

The deterministic benchmark runner prints total elapsed milliseconds and milliseconds per iteration. The timing runner prints sample count, average, minimum, and maximum milliseconds. Timing-sensitive sources are type-checked in CI but are not executed there and never impose pass/fail timing thresholds. Do not compare results across machines, compiler versions, power modes, or hosted CI runners as if they were equivalent.

## Baseline — 2026-11-14

Environment:

- Nox `2.1.111` from the checksum-pinned official macOS arm64 release archive;
- macOS 27.2, arm64;
- one process per benchmark source and backend;
- `NOX_POOL_WORKERS=2`;
- one observation per reported row, with no statistical confidence claim.

Cron results:

| Workload | Iterations | LLVM total | LLVM ms/iteration | QBE total | QBE ms/iteration |
|---|---:|---:|---:|---:|---:|
| Parse bounded complex expression | 20,000 | 69 ms | 0.0034 | 85 ms | 0.0043 |
| Dense next-fire (`*/5`) | 50,000 | 120 ms | 0.0024 | 153 ms | 0.0031 |
| Sparse next-fire (February 29) | 1,000 | 4,041 ms | 4.0410 | 4,490 ms | 4.4900 |

Due-collection results:

| Scenario | Jobs | Iterations | LLVM ms/collection | QBE ms/collection |
|---|---:|---:|---:|---:|
| None due | 100 | 100 | 0.0300 | 0.0400 |
| None due | 1,000 | 10 | 2.7000 | 3.7000 |
| None due | 10,000 | 1 | 299.0000 | 352.0000 |
| One due | 100 | 100 | 0.0300 | 0.0500 |
| One due | 1,000 | 10 | 3.7000 | 4.1000 |
| One due | 10,000 | 1 | 343.0000 | 400.0000 |
| All due | 100 | 10 | 0.2000 | 0.2000 |
| All due | 1,000 | 1 | 19.0000 | 23.0000 |
| All due | 10,000 | 1 | 2,192.0000 | 2,239.0000 |

## Optimized due-collection baseline — 2026-11-14

After the initial measurement, Chronos added bounded job/schedule identity dictionaries and replaced candidate insertion ordering with one deterministic composite-key sort. The workload was unchanged, but iteration counts were increased to keep optimized timings above the clock's millisecond resolution.

| Scenario | Jobs | Iterations | LLVM before | LLVM after | QBE before | QBE after |
|---|---:|---:|---:|---:|---:|---:|
| None due | 100 | 10,000 | 0.0300 ms | 0.0004 ms | 0.0400 ms | 0.0008 ms |
| None due | 1,000 | 1,000 | 2.7000 ms | 0.0030 ms | 3.7000 ms | 0.0040 ms |
| None due | 10,000 | 100 | 299.0000 ms | 0.0500 ms | 352.0000 ms | 0.0400 ms |
| One due | 100 | 10,000 | 0.0300 ms | 0.0008 ms | 0.0500 ms | 0.0008 ms |
| One due | 1,000 | 1,000 | 3.7000 ms | 0.0050 ms | 4.1000 ms | 0.0040 ms |
| One due | 10,000 | 100 | 343.0000 ms | 0.0400 ms | 400.0000 ms | 0.0400 ms |
| All due | 100 | 1,000 | 0.2000 ms | 0.0350 ms | 0.2000 ms | 0.0420 ms |
| All due | 1,000 | 100 | 19.0000 ms | 0.3900 ms | 23.0000 ms | 0.4400 ms |
| All due | 10,000 | 10 | 2,192.0000 ms | 5.0000 ms | 2,239.0000 ms | 4.8000 ms |

The checksums remained identical after the change. Existing scheduler tests plus explicit numeric-timestamp, lexical-ID, mixed-domain, reentrant removal, retry, overlap, and shutdown coverage passed on LLVM and QBE.

## Timing-sensitive integration baseline — 2026-11-15

Environment:

- checksum-pinned Nox `2.1.111` official macOS arm64 release;
- macOS 27.2 (build 26B123), arm64;
- `NOX_POOL_WORKERS=2`;
- one process per backend and one observation containing 20 or 40 samples per metric;
- millisecond-resolution monotonic observations, with no real-time or confidence-interval claim.

Metrics are intentionally distinct:

- **Wake latency** is raw Nox/OS `sleep_ms(5)` overshoot: observed monotonic elapsed time minus the requested sleep. It does not imply that Chronos owns a background worker.
- **Fixed-rate lateness** is handler-observed monotonic start minus `JobContext.scheduled_time_ms` while the application sleeps until each 20 ms deadline and then calls `tick()`.
- **Fixed-rate anchor drift** is the absolute difference between every planned context timestamp and `anchor + occurrence_index * 20 ms`.
- **Raw callback duration** is handler-local `Instant.elapsed_ms()` around `sleep_ms(5)`. Each one-shot callback is registered 10 ms ahead and awaited before `tick()` so registration-time clock movement cannot turn a zero-delay benchmark job into a past deadline.
- **Event callback duration** is the matching `succeeded` event's monotonic duration. It includes the synchronous `started` listener boundary documented in `docs/events.md`.

| Metric | Samples | Requested/interval | LLVM average (min–max) | QBE average (min–max) |
|---|---:|---:|---:|---:|
| Wake latency | 20 | 5 ms | 1.050 ms (0–2) | 1.200 ms (0–2) |
| Fixed-rate lateness | 40 | 20 ms | 3.250 ms (0–5) | 3.150 ms (0–5) |
| Fixed-rate anchor drift | 40 | 20 ms | 0.000 ms (0–0) | 0.000 ms (0–0) |
| Raw callback duration | 20 | 5 ms | 6.200 ms (5–7) | 6.250 ms (5–7) |
| Event callback duration | 20 | 5 ms | 6.200 ms (5–7) | 6.250 ms (5–7) |

The planned fixed-rate sequence retained its mathematical anchor on both backends. Observed start lateness was larger than the raw wake-overshoot baseline because it also includes application wake-to-`tick()` and scheduler dispatch work. These separately sampled averages must not be subtracted to manufacture an unsupported scheduler-overhead figure. Callback-local and event-observed durations matched in this observation, but that is not a precision guarantee.

## Interpretation

Chronos has no internal millisecond polling loop: the application explicitly decides when to call `tick()`. Every explicit tick still scans the bounded schedule list, so the no-due path remains O(n). Identity lookup is now expected O(1), and sorting is O(k log k) for `k` due candidates. The optimized 1,000→10,000 job measurements grow roughly in line with those bounds rather than the earlier quadratic curve.

The initial 10,000-job numbers justified the index/sort change. Across two optimized local runs, the 10,000-job none-due path ranged from 0.04–0.11 ms and the all-due path from 4.8–9.1 ms, illustrating ordinary host timing variation. A heap was deliberately not adopted: in the application-driven manual scheduler, the remaining bounded O(n) scan is already small, while a heap would introduce stale-entry invalidation and compaction obligations across reentrant mutation, retries, overlaps, enable/disable, and clock-domain changes. This decision can be revisited if background wake-deadline requirements or new measurements demonstrate a need.

These observations do not create a latency guarantee. Future optimizations must preserve deterministic ordering, mixed clock-domain separation, generation checks, overlap/misfire semantics, reentrant mutation behavior, and shutdown safety, and must be measured against this suite.
