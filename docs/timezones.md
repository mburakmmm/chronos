# Time zones

Status: deferred; UTC-only MVP.

Nox 2.1.0's documented `nox.time.DateTime` is UTC-only and provides no IANA timezone database. Chronos does not invent local-time or daylight-saving behavior on top of this API.

For the MVP:

- Cron expressions are evaluated in UTC.
- Calendar trigger fields are interpreted in UTC.
- Logs, help text, API documentation, and examples label calendar times as UTC.
- Fixed UTC offsets are not presented as named time zones.
- The machine locale or operating-system local zone is never inferred implicitly.
- Non-UTC timezone input is rejected rather than silently converted.

Future IANA timezone support requires a separate adapter, a licensed and versioned tzdata source, explicit ambiguous/nonexistent local-time policies, and transition tests. It is not part of the core MVP.
