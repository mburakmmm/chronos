#!/usr/bin/env python3
"""Chronos tool policy for Codex sessions and subagents."""

import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
RULES = (
    "Follow Chronos AGENTS.md. Route supported shell commands through RTK. "
    "Use rtk bypass only when exact output is required or RTK output is unusable. "
    "If a fresh Graphify graph exists, use graphify query/explain to orient before reading "
    "the relevant source. Use apply_patch for focused edits."
)


def output(event, **fields):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, **fields}}))


def graphify(payload, kind, graphify_exe):
    if not graphify_exe or not (ROOT / "graphify-out" / "graph.json").is_file():
        return ""
    args = [graphify_exe, "hook-guard", kind]
    if kind != "compact":
        args.append("--strict")
    result = subprocess.run(
        args, cwd=ROOT, input=json.dumps(payload), text=True, capture_output=True, timeout=3,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def pre(payload):
    tool = payload.get("tool_name")
    rtk = shutil.which("rtk")
    if tool == "Bash":
        command = payload["tool_input"]["command"]
        if not rtk:
            return "Install RTK and put it on PATH before running Chronos shell tools."
        check = subprocess.run(
            [rtk, "hook", "check", command], text=True, capture_output=True, timeout=3,
        )
        if check.returncode == 0:
            return "RTK supports this command. Retry with the RTK form (`rtk <command>`, or `rtk read` for file reads)."
        if check.returncode != 1 or not (check.stdout + check.stderr).startswith("No rewrite for:"):
            return "RTK could not check the command. Check the RTK installation."

    kind = "read" if tool in {"Read", "Glob"} else "search"
    graph_reply = graphify(payload, kind, shutil.which("graphify"))
    if graph_reply:
        fields = json.loads(graph_reply)["hookSpecificOutput"]
        if fields.get("permissionDecision") == "deny":
            return "Query the Chronos Graphify graph first, then retry with a targeted read or search."
        if fields.get("additionalContext"):
            output("PreToolUse", additionalContext=fields["additionalContext"])
    return None


def audit(payload):
    # Fixed tool names and size buckets only. No command, output, path or IDs.
    tool = payload.get("tool_name")
    if tool not in {"Bash", "Read", "Glob", "Grep"}:
        return
    response = payload.get("tool_response", "")
    size = len(json.dumps(response).encode("utf-8"))
    bucket = 0 if size < 1024 else 1 if size < 16384 else 2
    directory = ROOT / ".chronos-hook-audit"
    directory.mkdir(mode=0o700, exist_ok=True)
    with sqlite3.connect(directory / "counts.sqlite3", timeout=1) as db:
        db.execute("CREATE TABLE IF NOT EXISTS counts (tool TEXT, size_bucket INTEGER, "
                   "calls INTEGER NOT NULL, PRIMARY KEY (tool, size_bucket))")
        db.execute("INSERT INTO counts VALUES (?, ?, 1) ON CONFLICT(tool, size_bucket) "
                   "DO UPDATE SET calls = min(calls + 1, 2147483647)", (tool, bucket))


def main():
    event = sys.argv[1]
    payload = json.load(sys.stdin)
    if payload.get("hook_event_name") != event:
        return 0
    if event == "PreToolUse":
        try:
            reason = pre(payload)
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError):
            reason = "Chronos could not validate this tool call."
        if reason:
            print(reason, file=sys.stderr)
            return 2
    elif event == "PostToolUse":
        try:
            audit(payload)
        except (OSError, sqlite3.Error):
            print(json.dumps({"systemMessage": "Chronos could not write local hook counters."}))
    elif event in {"SessionStart", "SubagentStart"}:
        rules = RULES
        if not shutil.which("rtk"):
            rules += " Install RTK and ensure it is on PATH."
        if event == "SessionStart" and payload.get("source") == "compact":
            try:
                reminder = graphify(payload, "compact", shutil.which("graphify"))
            except (OSError, subprocess.TimeoutExpired):
                reminder = ""
            if reminder:
                rules += "\n" + reminder
        output(event, additionalContext=rules)
    return 0


if __name__ == "__main__":
    sys.exit(main())
