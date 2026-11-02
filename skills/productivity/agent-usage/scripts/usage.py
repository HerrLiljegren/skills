#!/usr/bin/env python3
"""Extract, record and compare token usage of agent runs from local transcripts.

Reads Claude Code session transcripts (~/.claude/projects) and Codex rollouts
(~/.codex/sessions). Only usage counts, models, timestamps and subagent
descriptions leave the transcript; message content is never copied.
"""

import argparse
import datetime as dt
import glob
import json
import os
import sys
from collections import defaultdict

LEDGER = os.environ.get(
    "AGENT_USAGE_LEDGER",
    os.path.expanduser("~/.local/share/agent-usage/runs.jsonl"),
)
FIELDS = ("uncached_in", "cache_write", "cache_read", "output", "reasoning")


def zero():
    return dict.fromkeys(FIELDS, 0)


def in_window(ts, since, until):
    return ts and (not since or ts >= since) and (not until or ts < until)


def jsonl(path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


# Claude Code: one transcript per session plus <session>/subagents/agent-*.jsonl.
# Streaming writes several entries per API message, so usage is deduplicated by message id.
def claude_thread(path, since, until):
    by_id = {}
    for entry in jsonl(path):
        message = entry.get("message") or {}
        usage = message.get("usage")
        model = message.get("model")
        if entry.get("type") != "assistant" or not usage or model == "<synthetic>":
            continue
        ts = entry.get("timestamp")
        if in_window(ts, since, until):
            by_id[message.get("id") or entry.get("uuid")] = (model, usage, ts)
    threads = defaultdict(lambda: {"turns": 0, "first": None, "last": None, **zero()})
    for model, usage, ts in by_id.values():
        t = threads[model]
        t["turns"] += 1
        t["first"] = min(filter(None, [t["first"], ts]))
        t["last"] = max(filter(None, [t["last"], ts]))
        t["uncached_in"] += usage.get("input_tokens", 0)
        t["cache_write"] += usage.get("cache_creation_input_tokens", 0)
        t["cache_read"] += usage.get("cache_read_input_tokens", 0)
        t["output"] += usage.get("output_tokens", 0)
        t["reasoning"] += (usage.get("output_tokens_details") or {}).get("thinking_tokens", 0)
    return threads


def claude_session(session, since, until):
    path = session if session.endswith(".jsonl") else None
    if not path:
        matches = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{session}.jsonl"))
        if len(matches) != 1:
            sys.exit(f"Claude session {session}: expected one transcript, found {len(matches)}")
        path = matches[0]
    rows = []
    for model, t in claude_thread(path, since, until).items():
        rows.append({"thread": "main", "description": "main session", "model": model, **t})
    for meta in sorted(glob.glob(path[:-6] + "/subagents/*.meta.json")):
        with open(meta, encoding="utf-8") as handle:
            info = json.load(handle)
        for model, t in claude_thread(meta[:-10] + ".jsonl", since, until).items():
            rows.append({
                "thread": os.path.basename(meta)[:-10],
                "description": info.get("description") or info.get("agentType") or "",
                "model": model,
                **t,
            })
    return "claude", path, rows


# Codex: one rollout per thread; subagents are separate rollouts whose session_meta
# names the parent. input_tokens includes cached_input_tokens, and reasoning tokens are
# part of output_tokens, so uncached input is the difference.
def codex_meta(path):
    for entry in jsonl(path):
        if entry.get("type") == "session_meta":
            return entry.get("payload") or {}
        return {}
    return {}


def codex_thread(path, since, until):
    threads = defaultdict(lambda: {"turns": 0, "first": None, "last": None, **zero()})
    model = "unknown"
    for entry in jsonl(path):
        payload = entry.get("payload") or {}
        if entry.get("type") == "turn_context":
            model = payload.get("model") or model
            continue
        if entry.get("type") != "token_usage_record":
            continue
        ts = entry.get("timestamp")
        if not in_window(ts, since, until):
            continue
        usage = payload.get("usage") or {}
        t = threads[model]
        t["turns"] += 1
        t["first"] = min(filter(None, [t["first"], ts]))
        t["last"] = max(filter(None, [t["last"], ts]))
        cached = usage.get("cached_input_tokens", 0)
        t["uncached_in"] += usage.get("input_tokens", 0) - cached
        t["cache_write"] += usage.get("cache_write_input_tokens", 0)
        t["cache_read"] += cached
        t["output"] += usage.get("output_tokens", 0)
        t["reasoning"] += usage.get("reasoning_output_tokens", 0)
    return threads


def codex_session(session, since, until):
    root = os.path.expanduser("~/.codex/sessions")
    rollouts = sorted(glob.glob(f"{root}/*/*/*/rollout-*.jsonl"))
    path = session if session.endswith(".jsonl") else None
    if not path:
        matches = [p for p in rollouts if p.endswith(f"{session}.jsonl")]
        if len(matches) != 1:
            sys.exit(f"Codex session {session}: expected one rollout, found {len(matches)}")
        path = matches[0]
    main_id = codex_meta(path).get("id")
    rows = [
        {"thread": "main", "description": "main session", "model": model, **t}
        for model, t in codex_thread(path, since, until).items()
    ]
    # Descendants at any depth; guardian (approval review) threads count as subagents too.
    parents, frontier = {main_id}, True
    metas = {p: codex_meta(p) for p in rollouts if p != path}
    while frontier:
        frontier = False
        for p, meta in metas.items():
            if meta.get("parent_thread_id") in parents and meta.get("id") not in parents:
                parents.add(meta.get("id"))
                frontier = True
                description = " ".join(filter(None, [
                    meta.get("thread_source"), meta.get("agent_role"), meta.get("agent_nickname"),
                ]))
                for model, t in codex_thread(p, since, until).items():
                    rows.append({"thread": meta.get("id"), "description": description, "model": model, **t})
    return "codex", path, rows


def extract(args):
    reader = codex_session if args.harness == "codex" else claude_session
    harness, path, rows = reader(args.session, args.since, args.until)
    return {"harness": harness, "transcript": path, "since": args.since, "until": args.until, "threads": rows}


def apply_roles(threads, mappings):
    for row in threads:
        row["role"] = "orchestrator" if row["thread"] == "main" else "subagent"
        for mapping in mappings:
            needle, _, role = mapping.partition("=")
            if needle.lower() in row["description"].lower():
                row["role"] = role
                break


def totals(threads, key):
    out = defaultdict(lambda: {"turns": 0, **zero()})
    for row in threads:
        bucket = out[key(row)]
        bucket["turns"] += row["turns"]
        for field in FIELDS:
            bucket[field] += row[field]
    return dict(out)


def cmd_extract(args):
    data = extract(args)
    apply_roles(data["threads"], args.role)
    json.dump(data, sys.stdout, indent=2)
    print()


def cmd_record(args):
    data = extract(args)
    apply_roles(data["threads"], args.role)
    run = {
        "recorded": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "label": args.label,
        "task": args.task,
        "size": args.size,
        "outcome": args.outcome,
        "notes": args.notes,
        **data,
        "by_model": totals(data["threads"], lambda r: r["model"]),
        "by_role": totals(data["threads"], lambda r: f"{r['role']} ({r['model']})"),
    }
    os.makedirs(os.path.dirname(args.ledger), exist_ok=True)
    with open(args.ledger, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(run) + "\n")
    print(f"Recorded {args.label!r} to {args.ledger}")
    print_run(run)


def fmt(n):
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(n)


def print_run(run):
    print(f"\n## {run['label']} · {run['harness']}" + (f" · {run['task']}" if run.get("task") else ""))
    for key in ("size", "outcome", "notes"):
        if run.get(key):
            print(f"{key}: {run[key]}")
    print("\n| Role (model) | Turns | Uncached in | Cache write | Cache read | Output |")
    print("|---|---|---|---|---|---|")
    for name, t in sorted(run["by_role"].items()):
        print(f"| {name} | {t['turns']} | {fmt(t['uncached_in'])} | {fmt(t['cache_write'])} "
              f"| {fmt(t['cache_read'])} | {fmt(t['output'])} |")


def cmd_compare(args):
    if not os.path.exists(args.ledger):
        sys.exit(f"No ledger at {args.ledger}")
    runs = [r for r in jsonl(args.ledger) if not args.label or any(s in r["label"] for s in args.label)]
    for run in runs:
        print_run(run)
    print("\n## Totals by model\n")
    print("| Run | Model | Turns | Uncached in | Cache write | Cache read | Output |")
    print("|---|---|---|---|---|---|---|")
    for run in runs:
        for model, t in sorted(run["by_model"].items()):
            print(f"| {run['label']} | {model} | {t['turns']} | {fmt(t['uncached_in'])} "
                  f"| {fmt(t['cache_write'])} | {fmt(t['cache_read'])} | {fmt(t['output'])} |")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("extract", "record"):
        p = sub.add_parser(name)
        p.add_argument("session", help="session id or transcript/rollout path")
        p.add_argument("--harness", choices=("claude", "codex"), required=True)
        p.add_argument("--since", help="UTC ISO timestamp, inclusive")
        p.add_argument("--until", help="UTC ISO timestamp, exclusive")
        p.add_argument("--role", action="append", default=[],
                       help="description-substring=role, first match wins; repeatable")
    record = sub.choices["record"]
    record.add_argument("--label", required=True)
    record.add_argument("--task")
    record.add_argument("--size")
    record.add_argument("--outcome")
    record.add_argument("--notes")
    record.add_argument("--ledger", default=LEDGER)
    compare = sub.add_parser("compare")
    compare.add_argument("--label", action="append", help="substring filter; repeatable")
    compare.add_argument("--ledger", default=LEDGER)
    args = parser.parse_args()
    {"extract": cmd_extract, "record": cmd_record, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
