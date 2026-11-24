# Phase 6 timezone prototype

The internal prototype maps local civil fields to UTC candidates using bounded transition tables. It lives under `proofs/timezone`. The public scheduler in Chronos 0.5.0 uses UTC.

## Data and scope

The fixture uses [IANA tzdata 2026f](https://data.iana.org/time-zones/releases/tzdata2026f.tar.gz), SHA-256 `01b4a91cec5167ed48c11e8ab78f2048cead78ce94b0cafcad0ae8c5a3044d3d`. The generator requires tzcode `zic` and `zdump` version `2022g`. It compiles the pinned data, extracts transitions from `zdump`, and checks their offsets with Python's standard-library `zoneinfo` using the compiled files. The fixture derives from public-domain IANA data. The archive's license lists BSD exceptions for specific code files, which are not included in the fixture. See the [upstream notice](https://data.iana.org/time-zones/tzdb/LICENSE).

The UTC coverage is 2024–2025 for Europe/Berlin and Australia/Lord_Howe and 1985–1987 for Asia/Kathmandu. A local coordinate must lie at least 24 hours after the coverage start and strictly before the coverage end minus 24 hours, so every candidate UTC instant under the supported offset bound lies within known coverage. The resolver rejects unknown fixtures and out-of-range coordinates. Each table supports up to 512 transitions. No host timezone is read during the Nox proof.

Reproduce the fixture and run the probe with Nox 2.1.111:

```sh
python3 scripts/generate_timezone_fixture.py /path/to/tzdata2026f.tar.gz | diff -u proofs/timezone/fixture.nox -
noxc run --backend llvm proofs/timezone/resolve_probe.nox
noxc run --backend qbe proofs/timezone/resolve_probe.nox
```

## Resolution rules to verify

- An ordinary local time resolves to one UTC instant.
- A repeated local time returns UTC candidates in increasing order. An explicit policy selects the first, last, both or neither.
- A nonexistent local time yields no candidates. Shift policies require separate definitions and tests.
- Historical UTC offsets may include seconds, and changes can be smaller than one hour. Keep the full offset when resolving a calendar timestamp.
- A ruleset revision changes the interpretation of future civil times. An eventual persistence format must record the zone, ruleset version and resolution policies. Reconciliation across versions needs an explicit migration.

## Civil input and provider contract

`LocalDateTime(year, month, day, hour, minute, second, millisecond)` validates proleptic Gregorian fields for years 1970–9999. Gregorian leap-year rules apply. The constructor accepts seconds 0–59 and milliseconds 0–999. It uses Nox's calendar conversion only to encode fields on an epoch-shaped wall coordinate. The zone provider supplies the offset rules that turn that coordinate into UTC instants.

The prototype `ZoneProvider` protocol exposes `version()` and `rules_for(zone_name)`. `resolve_civil(provider, expected_version, zone_name, civil)` requires a nonempty exact version match before looking up the zone. The generated provider uses explicit, case-sensitive IANA names. An unknown zone or version fails explicitly. Actual date coverage remains the narrower window declared by the returned rule table.

## Verified behavior and remaining work

LLVM and QBE agree at millisecond boundaries around Berlin gaps and folds, Lord Howe's half-hour DST transitions, and Kathmandu's historical 15-minute shift. A synthetic rule verifies second-resolution offsets. The civil probe also covers year 2000 versus 2100, invalid month lengths, invalid clock fields, and wrong or absent ruleset versions. A general-purpose data provider, local cron and persisted zoned schedules require separate validation.
