"""Price Claude token usage at Anthropic list rates and at gateway rates.

Standard library only (Python 3.9+), offline. Prices come from prices.json.

    python claude_cost.py estimate examples/scenarios.json
    python claude_cost.py estimate response.json --models claude-opus-5,claude-sonnet-5
    python claude_cost.py transcripts --since 2026-10-01      # Claude Code spend from local logs
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

PRICE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices.json")
FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_write_5m_tokens", "cache_write_1h_tokens", "output_tokens")
RATE_KEYS = ("input", "cache_read", "cache_write_5m", "cache_write_1h", "output")


def load_prices(path: str = PRICE_FILE) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def normalize(usage: dict) -> dict:
    """Map an Anthropic usage block (or our scenario format) onto FIELDS.

    cache_creation_input_tokens is split by TTL when the response says how;
    without a breakdown the writes are counted as 5-minute writes."""
    creation = usage.get("cache_creation") or {}
    one_hour = creation.get("ephemeral_1h_input_tokens", usage.get("cache_write_1h_tokens", 0)) or 0
    five_min = creation.get("ephemeral_5m_input_tokens")
    if five_min is None:
        five_min = usage.get("cache_write_5m_tokens", (usage.get("cache_creation_input_tokens", 0) or 0) - one_hour)
    return {
        "input_tokens": usage.get("input_tokens", 0) or 0,
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0) or 0,
        "cache_write_5m_tokens": max(five_min or 0, 0),
        "cache_write_1h_tokens": one_hour,
        "output_tokens": usage.get("output_tokens", 0) or 0,
    }


def price(usage: dict, model: str, column: str, prices: dict, effort: str | None = None):
    """USD for one normalized usage block, or None when the model has no rates."""
    entry = prices["models"].get(model)
    if not entry:
        return None
    rates = entry[column]
    total = sum(usage[field] * rates[key] for field, key in zip(FIELDS, RATE_KEYS)) / 1_000_000
    if column == "gateway" and effort:
        total *= entry.get("gateway_effort_multiplier", {}).get(effort, 1)
    return total


def cache_hit_ratio(usage: dict) -> float:
    prompt = usage["input_tokens"] + usage["cache_read_input_tokens"] + usage["cache_write_5m_tokens"] + usage["cache_write_1h_tokens"]
    return usage["cache_read_input_tokens"] / prompt if prompt else 0.0


def read_transcripts(root: str, since: str | None = None) -> dict:
    """Sum Claude Code usage per (model, effort) from transcript JSONL files.

    Claude Code writes one line per content block, so a response's usage repeats
    on several lines; each message id is counted once."""
    seen, totals = set(), defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                message = entry.get("message") or {}
                if entry.get("type") != "assistant" or "usage" not in message:
                    continue
                if since and entry.get("timestamp", "") < since:
                    continue
                key = message.get("id") or entry.get("requestId") or entry.get("uuid")
                if key in seen:
                    continue
                seen.add(key)
                usage = normalize(message["usage"])
                bucket = totals[(message.get("model", "?"), entry.get("effort"))]
                for field in FIELDS:
                    bucket[field] += usage[field]
    return dict(totals)


def money(value) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.4f}" if value < 1 else f"${value:,.2f}"


def estimate_command(args, prices) -> int:
    with open(args.file, encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict) and "scenarios" in data:
        items = [(s["name"], s["usage"], s.get("model")) for s in data["scenarios"]]
    else:
        items = [("usage", data.get("usage", data), data.get("model"))]
    models = args.models.split(",") if args.models else None
    print("| Scenario | Model | Anthropic list | Gateway | Cache hit |")
    print("|---|---|---:|---:|---:|")
    for name, raw, own_model in items:
        usage = normalize(raw)
        for model in models or [own_model or "claude-opus-5"]:
            print(f"| {name} | `{model}` | {money(price(usage, model, 'list', prices))}"
                  f" | {money(price(usage, model, 'gateway', prices))} | {cache_hit_ratio(usage):.0%} |")
    return 0


def transcripts_command(args, prices) -> int:
    totals = read_transcripts(os.path.expanduser(args.root), args.since)
    if not totals:
        print(f"no assistant messages with usage under {args.root}")
        return 1
    print("| Model | Effort | Input | Cache read | Cache write | Output | Anthropic list | Gateway |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    list_sum = gateway_sum = 0.0
    combined = dict.fromkeys(FIELDS, 0)
    for (model, effort), usage in sorted(totals.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        at_list, at_gateway = price(usage, model, "list", prices), price(usage, model, "gateway", prices, effort)
        list_sum += at_list or 0
        gateway_sum += at_gateway or 0
        for field in FIELDS:
            combined[field] += usage[field]
        writes = usage["cache_write_5m_tokens"] + usage["cache_write_1h_tokens"]
        print(f"| `{model}` | {effort or '-'} | {usage['input_tokens']:,} | {usage['cache_read_input_tokens']:,} | {writes:,}"
              f" | {usage['output_tokens']:,} | {money(at_list)} | {money(at_gateway)} |")
    print(f"\nTotal: {money(list_sum)} at Anthropic list price, {money(gateway_sum)} at gateway rates;"
          f" cache hit ratio {cache_hit_ratio(combined):.0%}.")
    if args.what_if:
        print(f"Same tokens on {args.what_if}: {money(price(combined, args.what_if, 'list', prices))} list,"
              f" {money(price(combined, args.what_if, 'gateway', prices))} gateway.")
    return 0


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Price Claude token usage.")
    parser.add_argument("--prices", default=PRICE_FILE)
    sub = parser.add_subparsers(dest="command", required=True)
    est = sub.add_parser("estimate", help="price a usage block, an API response or a scenarios file")
    est.add_argument("file")
    est.add_argument("--models", help="comma-separated model IDs to compare")
    tr = sub.add_parser("transcripts", help="price Claude Code transcripts")
    tr.add_argument("--root", default="~/.claude/projects")
    tr.add_argument("--since", help="ISO date, e.g. 2026-10-01")
    tr.add_argument("--what-if", help="also price all tokens on this model")
    args = parser.parse_args(argv)
    prices = load_prices(args.prices)
    return estimate_command(args, prices) if args.command == "estimate" else transcripts_command(args, prices)


if __name__ == "__main__":
    sys.exit(main())
