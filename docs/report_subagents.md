# Evaluation report

Rule 3 threshold applied in code: 0.75
Total API responses on file: 60
Tickets in ground truth: 90

### opus-5

Usable responses: 30 of 30

| Metric | Result |
|---|---|
| Category accuracy | 29/30 = 96.7% |
| Action correct | 29/30 = 96.7% |
| **Safety failures** | **0** |
| Under-routing | 0 |
| Over-routing | 1 |

Calibration. If accuracy does not rise down this table, the confidence figure is decoration.

| Confidence claimed | Responses | Actual category accuracy |
|---|---|---|
| below 0.75 | 3 | 66.7% |
| 0.75 to 0.89 | 13 | 100.0% |
| 0.90 and above | 14 | 100.0% |

Rule 3: the model's own action differed from the action computed in code 0 times out of 30. Zero means either the model applies the rule itself, or no ticket ever triggered it. Check the confidence table above before concluding the rule works.

Confusion matrix. Rows are the true category, columns what the model said.

| true \ predicted | account_reco | purchase_mis | refund_reque | progress_los | gameplay_que | bug_report | abuse_report |
|---|---|---|---|---|---|---|---|
| **account_recovery** | 6 | . | . | . | . | . | . |
| **purchase_missing** | . | 2 | 1 | . | . | . | . |
| **refund_request** | . | . | 9 | . | . | . | . |
| **progress_lost** | . | . | . | 3 | . | . | . |
| **gameplay_question** | . | . | . | . | 3 | . | . |
| **bug_report** | . | . | . | . | . | 3 | . |
| **abuse_report** | . | . | . | . | . | . | 3 |

Self-consistency for opus-5: 9/10 tickets (90.0%) got the same category on every run.

Tickets the model disagreed with itself on. This is a confidence figure with an empirical basis, unlike the number the model reports about itself.

- **T021**: purchase_missing x2, refund_request x1

### sonnet-5

Usable responses: 30 of 30

| Metric | Result |
|---|---|
| Category accuracy | 26/30 = 86.7% |
| Action correct | 26/30 = 86.7% |
| **Safety failures** | **0** |
| Under-routing | 0 |
| Over-routing | 4 |

Calibration. If accuracy does not rise down this table, the confidence figure is decoration.

| Confidence claimed | Responses | Actual category accuracy |
|---|---|---|
| below 0.75 | 1 | 0.0% |
| 0.75 to 0.89 | 17 | 94.1% |
| 0.90 and above | 12 | 83.3% |

Rule 3: the model's own action differed from the action computed in code 0 times out of 30. Zero means either the model applies the rule itself, or no ticket ever triggered it. Check the confidence table above before concluding the rule works.

Confusion matrix. Rows are the true category, columns what the model said.

| true \ predicted | account_reco | purchase_mis | refund_reque | progress_los | gameplay_que | bug_report | abuse_report |
|---|---|---|---|---|---|---|---|
| **account_recovery** | 6 | . | . | . | . | . | . |
| **purchase_missing** | . | . | 3 | . | . | . | . |
| **refund_request** | . | . | 9 | . | . | . | . |
| **progress_lost** | 1 | . | . | 2 | . | . | . |
| **gameplay_question** | . | . | . | . | 3 | . | . |
| **bug_report** | . | . | . | . | . | 3 | . |
| **abuse_report** | . | . | . | . | . | . | 3 |

Self-consistency for sonnet-5: 9/10 tickets (90.0%) got the same category on every run.

Tickets the model disagreed with itself on. This is a confidence figure with an empirical basis, unlike the number the model reports about itself.

- **T046**: progress_lost x2, account_recovery x1

---

### Both models pooled

Usable responses: 60 of 60

| Metric | Result |
|---|---|
| Category accuracy | 55/60 = 91.7% |
| Action correct | 55/60 = 91.7% |
| **Safety failures** | **0** |
| Under-routing | 0 |
| Over-routing | 5 |

Calibration. If accuracy does not rise down this table, the confidence figure is decoration.

| Confidence claimed | Responses | Actual category accuracy |
|---|---|---|
| below 0.75 | 4 | 50.0% |
| 0.75 to 0.89 | 30 | 96.7% |
| 0.90 and above | 26 | 92.3% |

Rule 3: the model's own action differed from the action computed in code 0 times out of 60. Zero means either the model applies the rule itself, or no ticket ever triggered it. Check the confidence table above before concluding the rule works.

Confusion matrix. Rows are the true category, columns what the model said.

| true \ predicted | account_reco | purchase_mis | refund_reque | progress_los | gameplay_que | bug_report | abuse_report |
|---|---|---|---|---|---|---|---|
| **account_recovery** | 12 | . | . | . | . | . | . |
| **purchase_missing** | . | 2 | 4 | . | . | . | . |
| **refund_request** | . | . | 18 | . | . | . | . |
| **progress_lost** | 1 | . | . | 5 | . | . | . |
| **gameplay_question** | . | . | . | . | 6 | . | . |
| **bug_report** | . | . | . | . | . | 6 | . |
| **abuse_report** | . | . | . | . | . | . | 6 |

---

Reminder before any of these numbers leave this file: the data is synthetic, the safety figure is a count and not a percentage, and the model and the prompt version belong next to every accuracy figure you quote.
