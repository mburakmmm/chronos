# IANA zoned cron

Chronos 0.6.0-dev supports experimental zoned cron through the single-owner persistent scheduler. Applications generate and compile a bounded provider for the IANA zones and UTC years they need. The general cron parser and the default in-memory examples use UTC.

## Data and scope

The fixture uses [IANA tzdata 2026f](https://data.iana.org/time-zones/releases/tzdata2026f.tar.gz), SHA-256 `01b4a91cec5167ed48c11e8ab78f2048cead78ce94b0cafcad0ae8c5a3044d3d`. The generator requires tzcode `zic` and `zdump` version `2022g`. It compiles the pinned data, extracts transitions from `zdump`, and checks their offsets with Python's standard-library `zoneinfo` using the compiled files. The fixture derives from public-domain IANA data. The archive's license lists BSD exceptions for specific code files, which are not included in the fixture. See the [upstream notice](https://data.iana.org/time-zones/tzdb/LICENSE).

The UTC coverage is 2024–2025 for Europe/Berlin and Australia/Lord_Howe and 1985–1987 for Asia/Kathmandu. A local coordinate must lie at least 24 hours after the coverage start and strictly before the coverage end minus 24 hours, so every candidate UTC instant under the supported offset bound lies within known coverage. The resolver rejects unknown fixtures and out-of-range coordinates. Each table supports up to 512 transitions. No host timezone is read during the Nox proof.

Reproduce the fixture and run the probe with Nox 2.2.70:

```sh
python3 scripts/generate_timezone_fixture.py /path/to/tzdata2026f.tar.gz | diff -u proofs/timezone/fixture.nox -
noxc run --backend llvm proofs/timezone/resolve_probe.nox
noxc run --backend qbe proofs/timezone/resolve_probe.nox
```

## Generate an application provider

Use the checksum-pinned archive above and put the generated Nox module in your application. Coverage ends at the start of the exclusive UTC end year.

```sh
python3 scripts/generate_timezone_fixture.py /path/to/tzdata2026f.tar.gz \
  --zone Europe/Berlin --zone Europe/Istanbul --zone Australia/Lord_Howe \
  --from-year 2024 --until-year 2031 > iana_rules.nox
```

The generator accepts up to 64 distinct explicit zone names, including IANA aliases in the pinned source, with a window of at most 100 years and up to 512 offset transitions per zone. At runtime the generated `IanaZoneProvider` is a Nox object. Chronos reads its version and zone rules without reading host tzdata or locale. Keep the exact generated module with the application's deployment artifacts and retain the old provider through migration. The example table covers the named zones from 2024 through 2030 UTC. [Persistent scheduler example](../examples/persistence/poll_zoned.nox)

The generator caps the compressed archive at 4 MiB and extracts the same bytes it verified. Stored zone names must use nonempty slash-separated components with no `.` or `..` components. [Security review](security.md#phase-6-iana-and-persistence-review)

## Resolution rules

- An ordinary local time resolves to one UTC instant.
- A repeated local time returns UTC candidates in increasing order. An explicit policy selects the first, last, both or neither.
- A nonexistent local time yields no candidates. Shift policies require separate definitions and tests.
- Historical UTC offsets may include seconds, and changes can be smaller than one hour. Keep the full offset when resolving a calendar timestamp.
- A ruleset revision can change the interpretation of future civil times. Persistent zoned records store the zone, ruleset version and resolution policies. Reconcile versions with an explicit migration.

## Civil input and provider contract

`LocalDateTime(year, month, day, hour, minute, second, millisecond)` validates proleptic Gregorian fields for years 1970–9999. Gregorian leap-year rules apply. The constructor accepts seconds 0–59 and milliseconds 0–999. It uses Nox's calendar conversion only to encode fields on an epoch-shaped wall coordinate. The zone provider supplies the offset rules that turn that coordinate into UTC instants.

The prototype `ZoneProvider` protocol exposes `version()` and `rules_for(zone_name)`. `resolve_civil(provider, expected_version, zone_name, civil)` requires a nonempty exact version match before looking up the zone. The generated provider uses explicit, case-sensitive IANA names. An unknown zone or version fails explicitly. Actual date coverage remains the narrower window declared by the returned rule table.

## Verified behavior and remaining work

LLVM and QBE agree at millisecond boundaries around Berlin gaps and folds, Lord Howe's half-hour DST transitions, and Kathmandu's historical 15-minute shift. A synthetic rule verifies second-resolution offsets. The civil probe also covers year 2000 versus 2100, invalid month lengths, invalid clock fields, and wrong or absent ruleset versions.

## Local cron proof

`LocalCronPrototype` borrows the existing five-field cron matcher for local calendar fields, including weekdays. It searches UTC segments in chronological order and uses each segment's offset to find matching local minutes. This preserves UTC ordering even when the local clock turns backward. The trigger requires a pinned provider version and explicit fold policy. The only supported gap policy is `skip`.

The prototype implements inclusive and exclusive UTC queries. It accepts references from the table's UTC start plus 48 hours through its UTC end minus 48 hours, exclusive. The same interval bounds returned occurrences and leaves enough rule coverage to classify ambiguous local times. Exhausting that interval returns `None`. Invalid references and matcher search exhaustion remain errors. Each query evaluates at most 2,048 local candidates.

The proof covers all four fold policies, nonexistent times, increasing UTC order, Lord Howe's half-hour transitions, a local weekday that differs from the UTC weekday, and second-resolution offsets. Run it with `noxc run --backend llvm proofs/timezone/local_cron_probe.nox` or use `--backend qbe`.

## Manual scheduler integration proof

`ManualLocalCronTrigger` adapts the prototype to `UtcTrigger`. Tests register it with `make_utc_job_with_policies` and drive `Scheduler` with `FakeClock`. Callback context contains the planned UTC millisecond and attempt number. The tests cover inclusive registration, both fold occurrences, a backward clock jump, an omitted spring gap and bounded catch-up.

Registration requires complete coverage. If completion or a late tick moves to or beyond the effective coverage end, the adapter's exclusive query returns `None` and clears the next run. This preserves the scheduler's normal late-occurrence policy while preventing replay of the final occurrence. Direct prototype queries still report an out-of-coverage reference. These contracts apply to the in-memory proof under `proofs/timezone`.

Run `noxc run --backend llvm proofs/timezone/manual_scheduler_probe.nox` and repeat with `--backend qbe`.

## Stored ruleset migration

The internal `cron-cursor-zoned` kind uses the existing SQLite v2 definition row. Its payload is `version|zone|fold|gap|cursor-utc-ms|expression`. Reading the payload checks that the supplied provider advertises the pinned version and that the cursor is an eligible match under that version. Opening SQLite leaves the stored value intact.

Migration is an explicit revision-checked write. It requires the old provider, the new provider, the new version, the current revision and an operator-selected UTC cutoff. Under the new rules, Chronos chooses the first eligible candidate strictly after the cutoff and at or after the old saved cursor. This avoids replay at or before the cutoff and prevents moving the pending cursor backward. Old pending occurrences may be dropped by that boundary. The contract is defined in UTC instants. A repeated civil label can resolve to a different UTC instant after a ruleset change.

Migration preserves the zone, cron expression, fold and gap policies, handler and enabled flag of a pending record. A missing matching version, stale revision or insufficient target coverage prevents the write. The proof exercises a version change with a synthetic revision, and extends an exhausted record with a second generated provider for the same `2026f` release.

When a record is exhausted, pass its revision, its original provider, the replacement provider and a UTC cutoff at or after the update that marked the row exhausted. The replacement may extend the same ruleset version or use another version. The write re-enables the definition at the first eligible UTC occurrence strictly after the cutoff. Retrying with a stale revision fails. Use a cutoff that the new provider covers.

## Stored zoned dispatch

Pass the provider as the optional fifth argument to `PersistentScheduler`. On a zoned record, the scheduler verifies the pinned ruleset and pending UTC occurrence. It accepts skip or fire-once misfires without retries. When a poll is due, it writes the next cursor after the observed UTC time using the current revision before invoking the trusted handler. A process exit after commit can lose that invocation. Earlier occurrences cannot be replayed by moving the wall clock backward.

When the rules have no later covered occurrence, dispatch commits an exhausted disabled record. The old payload remains available for inspection and subsequent polls return `exhausted`. One poll may still run the last covered occurrence according to its misfire policy. The scheduler reports `timezone-unavailable` for a zoned record with no configured provider, and `schedule-error` for a provider version or zone mismatch.

Run `python3 scripts/verify_persistence.py` with Nox 2.2.70. The SQLite tests reopen the database after both normal closure and process exit before commit, after commit or after a handler effect. They check fold ordering, clock rewind, persisted exhaustion and explicit resume with wider coverage.
