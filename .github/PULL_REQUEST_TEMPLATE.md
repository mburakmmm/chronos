## Summary

Describe the user-visible change and why it belongs in the current Chronos phase.

## Time and execution semantics

Explain UTC versus monotonic behavior, trigger boundaries, retry/misfire/overlap impact, and shutdown behavior. Write “not applicable” where appropriate.

## Verification

- [ ] Added or updated deterministic tests.
- [ ] Added or updated a compiling example for public behavior.
- [ ] Ran `python3 scripts/verify.py`.
- [ ] Ran `noxc fmt` on affected Nox files.
- [ ] Ran `git diff --check`.
- [ ] Verified affected LLVM/QBE behavior.

Commands and results:

```text
paste exact commands and summaries here
```

## Safety and compatibility

- [ ] Work remains bounded in jobs, catch-up, retries, overlap, listeners, and history.
- [ ] No secret, raw exception payload, or executable job definition is retained/logged.
- [ ] No exactly-once, timeout, persistence, timezone, or platform claim was added without evidence.
- [ ] Public API, compatibility, changelog, and migration notes are updated where needed.
- [ ] Any Nox compiler/runtime limitation is recorded with a reproducer.
