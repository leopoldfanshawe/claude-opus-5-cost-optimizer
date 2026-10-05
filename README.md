# Claude Opus 5.5 Cost Optimizer

A small, auditable cost estimator for long-running **Claude Opus 5.5** calls through Argolink. It separates uncached input, cached input, cache writes, and output so a budget review can explain where a number came from.

[Claude Opus 5.5 model page →](https://argolink.io/gh-claude-opus-5-cost-optimizer) · [Argolink API docs →](https://argolink.io/gh-unified-api-docs)

## Current facts

- Model ID: `claude-opus-5-5`; endpoint: `POST /v1/messages`.
- Context: 1,000,000 tokens; maximum output: 128,000 tokens.
- Effort values: `low`, `medium`, `high`, `xhigh`, `max`; default `medium`. Thinking is always on.
- Pricing: $4/M input, $20/M output, $0.20/M cached input, $5/M cache write.
- Forcing a tool with `tool_choice: any` or `tool_choice: tool` is unsupported; leave the model page's tool behavior in charge.

## Estimate

```bash
python estimate_cost.py examples/sample-usage.json
```

The estimator is intentionally offline. It never sends a request and never needs an API key. Use it before deciding whether to batch work, reuse a prompt prefix, or lower the requested effort.

## Boundaries

This repository does not promise a cheaper route or invent a second model. It only makes the Argolink price snapshot and budgeting arithmetic visible. Recheck the model page before publishing a quote.
