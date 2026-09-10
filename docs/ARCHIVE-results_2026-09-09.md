# Archive: results_raw as of 2026-09-09

Total responses: 136
Failed/unparseable: 1

| Model | Run | Responses | Unique tickets |
|---|---|---|---|
| claude-opus-5 | 1 | 10 | 10 |
| claude-opus-5 | 2 | 10 | 10 |
| claude-opus-5 | 3 | 5 | 5 |
| claude-sonnet-5 | 1 | 91 | 90 |
| claude-sonnet-5 | 2 | 10 | 10 |
| claude-sonnet-5 | 3 | 10 | 10 |

## Why this file is being archived rather than extended

It is internally inconsistent. The 10 hand-picked hard tickets were run three times on Sonnet and up to three
times on Opus, while the other 80 were run once, and the Opus pass over the full 90 was never completed. That
is fine for the questions it was built to answer, and wrong as a base for the next round, which needs an even
number of runs per ticket per model.

## What it established, and what still stands

These findings are recorded in 06-PROMPT-LOG.md under Round 2 and do not need to be re-derived:

- Sonnet 5 via the API, prompt v1, 110 responses covering all 90 tickets: 109/110 category accuracy,
  110/110 correct action, zero safety failures, zero under-routing, zero over-routing.
- The round 1 hypothesis that purchase_missing collapses into refund_request was refuted. 13 of 14 correct.
- Environment changes the answer: T021 failed 3/3 as a subagent and passed via the API, same prompt, same model.
- Rule 3 never fired. Zero of 110 Sonnet responses came back below 0.75.
- Calibration on 110 responses is correctly ordered: 98.0% in the 0.75-0.89 band, 100% at 0.90 and above.
- Three ground-truth labels were corrected (T023, T024, T018) and the label set is now frozen.

## Known gap this file cannot close

Most tickets have a single pass, so a correct answer cannot be distinguished from a correct-this-time answer.
That is what the next round is for.
