# Claude Opus 5 cost optimizer — from $1.60 per 1M input tokens (Opus 5.5)

**Anthropic Claude Opus 5 is live on [ArgoLink](https://argolink.io/gh-claude-opus-5-cost-optimizer)**: $2 per 1M input tokens, $10 output, $0.20 cached input; Opus 5.5 is $1.60 / $8 / $0.08, all 60% below Anthropic's list price. Both have a 1M-token context, up to 128K output tokens, effort from `low` to `max`, and prompt caching for 5 minutes or 1 hour.

[Price reference](#price-reference) · [Levers](#the-levers-ranked) · [Opus 5 vs 5.5](#opus-5-vs-opus-55-what-changes-the-bill) · [Monthly scenarios](#monthly-scenarios) · [Spend analyzer](#price-your-own-usage) · [FAQ](#faq)

This repo is a cost guide with numbers you can recompute: a dated price file, an offline estimator, and an analyzer that prices your Claude Code transcripts at list and gateway rates.

<sub>Prices checked 2026-10-07 against [Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing) and the [model pages](https://argolink.io/en/models/claude-opus-5). Unofficial; not affiliated with Anthropic.</sub>

## Price reference

USD per 1M tokens. A 5-minute cache write costs 1.25× the input rate and a 1-hour write 2×, in both columns.

| Model | | Input | 5-min cache write | 1-hour cache write | Cache read | Output |
|---|---|---:|---:|---:|---:|---:|
| `claude-opus-5-5` | Anthropic | $4 | $5 | $8 | $0.20 | $20 |
| | ArgoLink | **$1.60** | **$2** | **$3.20** | **$0.08** | **$8** |
| `claude-opus-5` | Anthropic | $5 | $6.25 | $10 | $0.50 | $25 |
| | ArgoLink | **$2** | **$2.50** | **$4** | **$0.20** | **$10** |
| `claude-fable-5-1` | Anthropic | $10 | $12.50 | $20 | $0.25 | $50 |
| | ArgoLink | **$4** | **$5** | **$8** | **$0.10** | **$20** |
| `claude-sonnet-5` | Anthropic | $2 | $2.50 | $4 | $0.20 | $10 |
| | ArgoLink | **$0.80** | **$1** | **$1.60** | **$0.08** | **$4** |
| `claude-opus-4-8` | Anthropic | $5 | $6.25 | $10 | $0.50 | $25 |
| | ArgoLink | **$2** | **$2.50** | **$4** | **$0.20** | **$10** |

The same numbers, with sources, are in [`prices.json`](./prices.json). Reasoning tokens bill as output. Neither price list adds a long-context surcharge for these models: a 900K-token prompt costs the same per token as a 9K one.

## The levers, ranked

| Lever | What it saves | Applies to | Source |
|---|---|---|---|
| Gateway rate | 60% on every token type | all Claude models above | model pages |
| Prompt caching | a cached read costs 10% of input (5% on Opus 5.5, 2.5% on Fable 5.1) | repeated prefixes: system prompts, tools, documents, agent history | Anthropic pricing |
| Opus 5 → Opus 5.5 | 20% per token, and half the relative cache-read price | Opus workloads that already run with thinking | Anthropic pricing |
| Effort | fewer thinking tokens, which bill as output | every thinking model; Opus 5.5 defaults to `medium`, Opus 5 to `high` | Anthropic effort docs |
| Routing to Sonnet 5 | half of Opus 5.5's output rate, 60% below Opus 5 | well-specified edits, extraction, summaries | price reference above |
| Batch API | 50% on input and output | asynchronous work on Anthropic's own API; the gateway's pages list no batch endpoint | Anthropic pricing |
| Avoid `max` on Fable 5.1 | the gateway bills `max` effort at 3×, which is 1.2× Anthropic's list price | Fable 5.1 through the gateway | Fable 5.1 model page |

### Caching, worked out

A cache write pays for itself after one read at the 5-minute TTL (1.25× then 0.1×) and after two reads at the 1-hour TTL (2× then 0.1×). Example: a 20,000-token system prompt and tool block on Opus 5.5 through the gateway, used by 10 requests within five minutes.

| | Cost of the prefix |
|---|---:|
| No caching: 10 × 20,000 × $1.60 / 1M | $0.320 |
| Cached: one 5-minute write ($0.040) + 9 reads ($0.0144) | $0.054 |

Two traps cost money silently:

- **Below the minimum, `cache_control` is ignored without an error.** The minimum is 512 tokens on Opus 5.5, Opus 5 and both Fable models, 1,024 on Opus 4.8 and Sonnet 5. A response with `cache_creation_input_tokens` and `cache_read_input_tokens` both at 0 was not cached.
- **The 1-hour TTL only pays when you come back.** It doubles the write price; use it for prefixes reused across pauses longer than five minutes, such as an agent session you return to after lunch.

## Opus 5 vs Opus 5.5: what changes the bill

Opus 5.5 is cheaper per token, but some workloads spend more tokens on it.

| Change | Effect on cost |
|---|---|
| $4 / $20 instead of $5 / $25 (list) | 20% lower on every token type |
| Cache read at 0.05× input instead of 0.1× | agent loops and long chats, which are mostly cache reads, drop by more than 20% |
| Thinking always on; `thinking: {"type": "disabled"}` returns 400 | a workload that ran Opus 5 without thinking now pays for thinking tokens as output |
| Default effort `medium` instead of `high` | requests that leave effort unset think less |
| Forcing a tool with `tool_choice` `any` or `tool` returns 400 | no cost change, but the request fails until you switch to `auto` |

Example of the third row: 1,000 classification requests of 2,000 input and 200 output tokens. On Opus 5 with thinking disabled that is $6.00 through the gateway ($15 at list). If Opus 5.5 adds 500 thinking tokens per request even at `low` effort, the same job costs $8.80 ($22 at list). Measure your own thinking overhead before moving such jobs; Opus 5 remains available.

## Monthly scenarios

From [`examples/scenarios.json`](./examples/scenarios.json), priced by `python claude_cost.py estimate examples/scenarios.json --models claude-opus-5,claude-opus-5-5,claude-sonnet-5`. The token counts are assumptions stated in the file, not measurements.

| Scenario | Model | Anthropic list | Gateway | Cache hit |
|---|---|---:|---:|---:|
| Support assistant: 60,000 requests a month, 6K-token cached context | `claude-opus-5` | $1,181.25 | $472.50 | 88% |
| | `claude-opus-5-5` | $873.00 | $349.20 | 88% |
| | `claude-sonnet-5` | $472.50 | $189.00 | 88% |
| Coding team: 5 developers, 200 Claude Code sessions a month | `claude-opus-5` | $1,040.00 | $416.00 | 91% |
| | `claude-opus-5-5` | $732.00 | $292.80 | 91% |
| | `claude-sonnet-5` | $416.00 | $166.40 | 91% |
| Contract review batch: 10,000 documents of 30K tokens | `claude-opus-5` | $1,886.25 | $754.50 | 6% |
| | `claude-opus-5-5` | $1,505.00 | $602.00 | 6% |
| | `claude-sonnet-5` | $754.50 | $301.80 | 6% |

The batch has almost nothing to cache, so its savings come from the rate and from model choice. On Anthropic's API it would also qualify for the 50% Batch API discount, which brings Opus 5.5 at list price to $752.50, still above the gateway's $602.00.

## Price your own usage

[`claude_cost.py`](./claude_cost.py) is offline and needs only Python 3.9+.

**One response, a usage block or a scenarios file**

```bash
python claude_cost.py estimate examples/response.json --models claude-opus-5-5,claude-opus-5
```

```
| Scenario | Model | Anthropic list | Gateway | Cache hit |
|---|---|---:|---:|---:|
| usage | `claude-opus-5-5` | $0.1846 | $0.0738 | 87% |
| usage | `claude-opus-5` | $0.2547 | $0.1019 | 87% |
```

It reads `cache_creation.ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens` from the response to price each write at its own TTL.

**Your Claude Code history**

```bash
python claude_cost.py transcripts --since 2026-10-01 --what-if claude-sonnet-5
```

Claude Code keeps a JSONL transcript per session under `~/.claude/projects/`, with subagent transcripts in a folder next to it. The analyzer sums the `usage` of every assistant message once (Claude Code repeats a response's usage on each of its content-block lines), groups it by model and effort, and prints input, cache reads, cache writes, output, and the cost at list and gateway rates, then the total and the cache-hit ratio. `--what-if` reprices all the tokens on another model. Nothing is sent anywhere.

**Claude Code's own numbers**

`/usage` and the status line price tokens at Anthropic list rates. A managed `modelPricing` setting with `"multiplier": 0.4` scales them to the gateway's rates for Claude models; Claude Code reads it only from managed settings, for example `/Library/Application Support/ClaudeCode/managed-settings.json` on macOS or `/etc/claude-code/managed-settings.json` on Linux (v2.1.242 or later).

## Setup in one line per client

| Client | Setting |
|---|---|
| Anthropic SDKs | `ANTHROPIC_BASE_URL=https://argolink.io`, key in `ANTHROPIC_API_KEY` |
| Claude Code | `env` in `~/.claude/settings.json`: `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN` |
| cURL | `POST https://argolink.io/v1/messages` with `x-api-key` and `anthropic-version: 2023-06-01` |

## FAQ

**Is the 1M context window more expensive per token past 200K?**
No. Anthropic bills the full 1M window at standard rates for Claude 4.6 and later models, and the gateway lists no surcharge for Claude. The OpenAI models on the same gateway do carry one above 272K tokens; Claude does not.

**Which is cheaper for Claude Code, Opus 5 or Opus 5.5?**
Opus 5.5 in almost every session, because sessions are mostly cache reads and Opus 5.5 reads cache at $0.08 instead of $0.20 per 1M through the gateway. In the coding-team scenario it costs $292.80 a month against $416.00.

**Does thinking count as output?**
Yes, on every model and price list here, even when the thinking text is not returned to you.

**Why does `claude_cost.py transcripts` show `n/a` for some rows?**
The model has no entry in `prices.json`, for example a non-Claude model or Claude Code's `<synthetic>` placeholder messages. Add a row to the file to price it.

**How do I check the prices are still current?**
Each row of `prices.json` names its source page and the check date. Re-check the pages before a budget decision; they win if they differ.

## Run the tests

```bash
pip install pytest
pytest tests/
```

The tests use small synthetic transcripts and make no network calls.

## License

MIT
