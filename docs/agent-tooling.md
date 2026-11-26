# Chronos agent tooling

The repository's [Codex hook configuration](../.codex/hooks.json) applies to main sessions and subagents. It requires Git, Python 3 and RTK on the hook process's PATH. Review the project hooks with `/hooks` in a trusted Chronos checkout. Codex requires a new review when a hook definition changes. [Codex hook configuration and trust](https://developers.openai.com/codex/hooks)

- Session and subagent startup supply the same tool policy. After compaction, the session hook restores the policy and resets Graphify's session counters when a graph is available.
- The Bash hook checks commands using `rtk hook check`. It rejects commands RTK knows how to rewrite and asks the caller to use the RTK form. Commands RTK reports as unsupported and intentional `rtk bypass` calls proceed through normal Codex permissions. Use bypass when a task needs exact output and RTK's summary is insufficient.
- Graphify is optional. When `graphify-out/graph.json` exists, use Graphify to orient source discovery. The hook passes shell reads and searches to Graphify's guard. Graphify's installed guard treats Bash as advisory and can redirect dedicated Read/Grep calls when the client exposes those tool names. Graphify output is local.
- The post-tool hook retains aggregate counts in the ignored `.chronos-hook-audit/counts.sqlite3` file. It stores fixed tool categories and three response-size buckets.

The Bash hook can run alongside the user-level RTK hook. An explicitly prefixed command passes the project check and the RTK rewriter can leave it as supplied. Tools without a matching Codex hook event follow the repository policy in [AGENTS.md](../AGENTS.md).
