# Evaluation report

Rule 3 threshold applied in code: 0.75
Total API responses on file: 111
Tickets in ground truth: 90

### claude-sonnet-5

Usable responses: 110 of 111 (1 unparseable or failed)

| Metric | Result |
|---|---|
| Category accuracy | 109/110 = 99.1% |
| Action correct | 110/110 = 100.0% |
| **Safety failures** | **0** |
| Under-routing | 0 |
| Over-routing | 0 |

Calibration. If accuracy does not rise down this table, the confidence figure is decoration.

| Confidence claimed | Responses | Actual category accuracy |
|---|---|---|
| below 0.75 | 0 | n/a |
| 0.75 to 0.89 | 49 | 98.0% |
| 0.90 and above | 61 | 100.0% |

Rule 3: the model's own action differed from the action computed in code 0 times out of 110. Zero means either the model applies the rule itself, or no ticket ever triggered it. Check the confidence table above before concluding the rule works.

Confusion matrix. Rows are the true category, columns what the model said.

| true \ predicted | account_reco | purchase_mis | refund_reque | progress_los | gameplay_que | bug_report | abuse_report |
|---|---|---|---|---|---|---|---|
| **account_recovery** | 18 | . | . | . | . | . | . |
| **purchase_missing** | . | 13 | . | . | . | . | . |
| **refund_request** | . | . | 19 | . | . | . | . |
| **progress_lost** | . | . | . | 16 | . | . | . |
| **gameplay_question** | . | . | . | . | 16 | . | . |
| **bug_report** | . | . | . | . | 1 | 16 | . |
| **abuse_report** | . | . | . | . | . | . | 11 |

Self-consistency for claude-sonnet-5: 10/10 tickets (100.0%) got the same category on every run.

---

Reminder before any of these numbers leave this file: the data is synthetic, the safety figure is a count and not a percentage, and the model and the prompt version belong next to every accuracy figure you quote.
