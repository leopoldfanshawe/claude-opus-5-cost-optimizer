# Budgeting workflow

1. Record token counts from the completed response, separated into input, output, cached input, and cache writes.
2. Run `estimate_cost.py` against that record.
3. Compare the result with the model page's current rates.
4. Decide whether prompt-prefix reuse, smaller context, or a lower effort is acceptable.

Caching is not free: cached input is cheaper than normal input, while cache writes have their own rate. A single total-token number hides that difference.
