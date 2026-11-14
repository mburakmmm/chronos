# Benchmarks

Status: Phase 4 measurement infrastructure. Benchmark timings are observations, not API guarantees or CI pass/fail thresholds.

## Scope

The initial suite measures:

- parsing one bounded, nontrivial five-field UTC cron expression;
- dense (`*/5`) and sparse (February 29) next-fire calculation;
- scheduler due collection with 100, 1,000, and 10,000 jobs;
- no due jobs, one due job, and all jobs due at the same timestamp.

`due_lookup_benchmark.nox` calls the scheduler's internal `_collect_due` operation. Its setup directly constructs valid registry and schedule entries so public registration cost, callback execution, event delivery, and rescheduling do not contaminate the due-collection measurement. This is benchmark-only access and does not make `_collect_due`, `RegisteredJob`, `ScheduledEntry`, or `DueItem` public API.

The benchmark retains result checksums so the measured work remains observable. Chronos uses Nox's monotonic `Instant.elapsed_ms()` for timing. Each benchmark is an ahead-of-time compiled process, so no JIT warm-up policy is implied.

## Running

Run both verified backends from the repository root:

```sh
python3 scripts/run_benchmarks.py
```

Select an exact compiler without changing the installed Nox toolchain:

```sh
NOXC=/absolute/path/to/noxc python3 scripts/run_benchmarks.py
```

The runner prints total elapsed milliseconds and milliseconds per benchmark iteration. Do not compare results across machines, compiler versions, power modes, or hosted CI runners as if they were equivalent.

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

## Interpretation

Chronos has no internal millisecond polling loop: the application explicitly decides when to call `tick()`. However, every explicit tick currently scans the full schedule list. `_collect_due` also performs a linear registry lookup for every schedule, and due candidates are ordered with insertion sort. The roughly 95–115× increase when moving from 1,000 to 10,000 jobs is consistent with quadratic work in the current representation.

The 10,000-job numbers are not an acceptable basis for claiming low-latency large-registry scheduling. They provide concrete justification to evaluate an indexed registry plus a deterministic due-time structure. No data structure has been changed yet. Any optimization must preserve deterministic ordering, mixed clock-domain separation, generation checks, overlap/misfire semantics, reentrant mutation behavior, and shutdown safety. A replacement must be benchmarked against this same suite and covered by regression tests before adoption.
