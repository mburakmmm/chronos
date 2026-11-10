# UTC cron dialect

Status: Phase 0 grammar contract; implementation begins in Chronos 0.1.0.

## Time basis and fields

Chronos MVP cron expressions use UTC and exactly five fields:

```text
minute hour day-of-month month day-of-week
```

| Field | Range |
|---|---:|
| minute | 0..59 |
| hour | 0..23 |
| day-of-month | 1..31 |
| month | 1..12 |
| day-of-week | 0..6, Sunday = 0 |

Day-of-week `7` is rejected in the MVP. Month/weekday names, seconds, years, macros, and Quartz extensions are not accepted.

## Grammar

Each field is an ASCII comma-separated list of items. An item is one of:

- `*`
- an unsigned decimal literal, such as `5`
- an inclusive ascending range, such as `1-5`
- `*/step`, such as `*/15`
- `range/step`, such as `1-10/2`

Steps must be positive. A step attached to a single literal is rejected because it adds no useful schedule meaning and is easy to misread.

Whitespace separates fields. Empty fields, leading/trailing commas, duplicate separators, signed numbers, non-ASCII digits, reversed ranges, out-of-range values, and trailing text are errors.

Repeated values are normalized into sorted unique allowed-value sets. The parser never calls a shell, operating-system cron, evaluator, or callback.

## Day-of-month and day-of-week

Chronos uses traditional cron OR semantics when both day fields are restricted:

- both wildcard: every valid calendar day;
- only day-of-month restricted: day-of-month must match;
- only day-of-week restricted: day-of-week must match;
- both restricted: either field may match.

This rule is fixed for the MVP and covered by contract tests.

## Next-fire contract

`next_fire_after(reference_utc_ms)` is strictly exclusive. Results land on UTC minute boundaries with seconds and milliseconds equal to zero.

The implementation advances calendar fields rather than performing an unbounded minute-by-minute scan. It checks leap years, month lengths, February 29, and year rollover.

Malformed input is a parse error. A valid expression that has no match inside the search bounds returns a distinct no-next-fire/search-horizon result.

## Resource bounds

Initial MVP limits:

- maximum expression length: 256 ASCII characters;
- exactly five fields;
- maximum 128 comma/range items before normalization;
- maximum expanded unique values: the natural field total (134 across all fields);
- default search horizon: 8 calendar years after the reference;
- hard calendar-transition iteration limit: 100,000.

The implementation may use tighter internal bounds if tests show they preserve every supported expression. Bounds are configuration/internal constants, not an invitation to run indefinitely.

## Examples

```text
*/15 * * * *   every 15 minutes UTC
0 9 * * 1-5    09:00 UTC Monday through Friday
0 0 1 * *      00:00 UTC on the first day of each month
0 0 29 2 *     00:00 UTC on February 29 in leap years
0 0 * * 0      00:00 UTC every Sunday
```

These are UTC expressions, not local-time schedules.
