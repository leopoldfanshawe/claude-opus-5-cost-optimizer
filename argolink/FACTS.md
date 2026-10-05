# Checked Argolink facts

Checked 2026-10-04 against the model catalog.

- `claude-opus-5-5`; `POST /v1/messages`.
- 1,000,000 context; 128,000 maximum output.
- Effort: low, medium, high, xhigh, max; default medium; thinking always on.
- Input $4/M; output $20/M; cached input $0.20/M; cache write $5/M.
- Forcing a tool with `tool_choice` type `any` or `tool` errors; do not use those values in examples.
