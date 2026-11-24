# Phase 6 timezone prototype proposal

The initial prototype would map a local civil timestamp in an explicitly named IANA zone to UTC using a pinned transition table. The application would supply the zone and rules. Chronos 0.5.0 uses UTC scheduling.

## Data and scope

The candidate input is IANA tzdata 2026f. Before generating fixtures, pin the exact source archive, tool version and checksum. Retain the upstream license notice and record the version and coverage window in the generated output. The upstream license describes public-domain data and exceptions for specific code files. See the [IANA release index](https://www.iana.org/time-zones) and [license](https://data.iana.org/time-zones/tzdb/LICENSE).

Start with a small reference corpus for Europe/Berlin, Australia/Lord_Howe and Asia/Kathmandu. Generate transition fixtures offline from the pinned archive and compare with the output from the IANA reference tools. Keep runtime inputs independent of the host timezone, locale and database. Reject unknown zones and timestamps outside the fixture's explicit range.

## Resolution rules to verify

- An ordinary local time resolves to one UTC instant.
- A repeated local time returns UTC candidates in increasing order. The policy must select the first, last, both or neither explicitly.
- A nonexistent local time reports a gap. The first prototype can skip it. Any shift policy needs its own definition and tests.
- Historical UTC offsets may include seconds, and changes can be smaller than one hour. Keep the full offset when resolving a calendar timestamp.
- A ruleset revision changes the interpretation of future civil times. An eventual persistence format must record the zone, ruleset version and resolution policies. Reconciliation across versions needs an explicit migration.

## Prototype exit checks

Verify equivalent LLVM and QBE results at and around gap and fold boundaries, plus ordinary times on either side. Include a southern-hemisphere transition, a half-hour DST change and a historical non-hour base offset. Keep the UTC scheduler and formats outside the prototype. Review the verified converter before connecting it to cron or persistence.
