# Prompt test log

Fill the three empty columns as you go. Nothing else.

Two sections: the results table, and the change log underneath. The change log is the part that turns "I tuned the prompt" into "I made these changes and here is what each one bought," which is a different quality of answer in an interview.

---

## Round 1 — prompt v1, hand test

Date: 2026-09-08
Prompt version: v1, kept verbatim in `07-PROMPT-VERSIONS.md`
Model: **Sonnet 5**, via the claude.ai chat interface, one fresh chat per ticket

The model matters and belongs in every result you report. If the classification script ends up calling a different model, none of the round 1 findings below carry over and the hand test has to be rerun. Record the model alongside every accuracy figure, here and in the README.

Ten tickets chosen to cover all seven categories, four deliberately ambiguous cases, one tone test, and the two tickets most likely to produce a genuine safety failure.

| Ticket | Expected category | Expected action | Model category | Model action | Conf. | What it latched onto (fill only when wrong) |
|---|---|---|---|---|---|---|
| T007 | account_recovery | hard_stop | account_recovery | hard_stop | 0.85 | correct |
| T009 | account_recovery | hard_stop | account_recovery | hard_stop | 0.90 | correct; flagged bug_report as secondary, which is the right read |
| T033 | refund_request | hard_stop | refund_request | hard_stop | 0.97 | correct, secondary purchase_missing. Weak test: rule 1 names this exact case verbatim, hence the 0.97 |
| T035 | refund_request | hard_stop | refund_request | hard_stop | 0.95 | correct, secondary bug_report. This is the real rule 1 test: the bug/refund pairing is nowhere in the prompt, so the rule generalised |
| T046 | progress_lost | human_review | progress_lost | human_review | 0.70 | correct. First sub-threshold confidence, and appropriately so. But rule 3 is unobservable here: progress_lost already maps to human_review, so we cannot tell whether the rule fired. Did not flag account_recovery as secondary, which it arguably should have |
| T023 | ~~purchase_missing~~ refund_request | ~~human_review~~ hard_stop | refund_request | hard_stop | 0.85 | **LABEL WAS WRONG, corrected.** See the label corrections section below |
| T021 | purchase_missing | human_review | refund_request | hard_stop | 0.90 | **MISS. Label stands, model is wrong.** Rule 4 violated: the word THEFT pushed it to refund_request. The ticket contains no request for money back. See the rule 1 over-trigger finding below |
| T057 | gameplay_question | auto_draft | gameplay_question | auto_draft | 0.85 | correct. "is that a bug or a rule" did not derail it, so the model reads the ask rather than the vocabulary. This narrows the T021 diagnosis: the failure is specific to the money boundary, not general keyword-following |
| T072 | bug_report | auto_draft | bug_report | auto_draft | 0.85 | correct. Control passed |
| T084 | abuse_report | hard_stop | abuse_report | hard_stop | 0.90 | correct, secondary account_recovery. Rule 2 did not over-fire, unlike rule 1 |

Why each one is in the list:

- **T007, T009** — `account_recovery` written entirely in the vocabulary of a bug report. These are the only two in the set that can produce a real safety failure.
- **T033** — spans `purchase_missing` and `refund_request`. Tests rule 1.
- **T035** — spans `bug_report` and `refund_request`. Tests rule 1 in the other direction.
- **T046** — `progress_lost` that sounds like `account_recovery`. Tests the boundary from the other side.
- **T023** — `purchase_missing` that drifts toward a refund at the end.
- **T021** — angry, all caps, otherwise ordinary. Tests rule 4: tone is not signal.
- **T057** — a rules question that contains the words "is that a bug". Tests whether the model reads the ask or the vocabulary.
- **T072** — a clean `bug_report`. A control. If this one is wrong, something bigger is broken.
- **T084** — `abuse_report` where the victims have an account problem. Tests rule 2 without breaking it.

### How to read your results

**Stop immediately if T007 or T009 come back as `auto_draft`.** That is the safety failure the whole design exists to prevent, and no other result matters until it is fixed. Fix the `account_recovery` definition, not the rules list.

**A wrong category with the right action is a minor miss.** If T046 comes back as `account_recovery`, the action goes from `human_review` to `hard_stop`, which is over-routing. Note it, do not chase it.

**Two or more of T033, T035, T084 landing on the less restrictive category means rule 1 is not carrying its weight.** Rewrite it, or better, move the disambiguation into the category definitions themselves, which is where it works more reliably.

**Everything else: note it and move on.** You are checking whether the prompt is roughly sound, not tuning it to ten examples. Tuning against ten cases you can see is how you end up with a prompt that scores well on those ten and badly on the other eighty.

---

### Round 1 result

Ten tested. Nine correct on both category and action. One miss. One label found to be wrong and corrected.

**The headline: zero safety failures.** T007 and T009, the two tickets in the whole dataset capable of producing one, both came back `account_recovery` / `hard_stop`. The guardrail held on the cases it exists for.

Rule by rule:

| Rule | Verdict |
|---|---|
| 1, most restrictive wins | Generalised. T035 proves it: the bug/refund pairing appears nowhere in the prompt. But it over-triggers, see the finding below |
| 2, account control wins | Held without over-firing. T084 kept `abuse_report` and put `account_recovery` in the secondary field, which is the correct read |
| 3, low confidence downgrades | **Untested.** Never observable in this set, see the open finding below |
| 4, tone is not signal | **Failed once.** T021, where THEFT moved the classification |
| 5, do not invent | **Failed once**, same ticket. The reason field asserted a money-back demand the player never made |

The `secondary_category` field earned its place. It fired on four of ten and was right every time, including where the primary was wrong.

**Do not read 9 out of 10 as 90 percent.** These ten were hand-picked to be hard, so the sample is not representative in either direction: the ambiguous cases are heavily over-represented, which pushes the number down, while each ticket got a fresh chat with nothing else in context, which pushes it up. The figure that goes in the README comes from the full 90, run through code, and nothing else.

**Decision: prompt v1 goes into the full run unchanged.** The single miss is a hypothesis about rule 1, not a confirmed pattern, and rewriting the prompt now would mean tuning against ten examples that are already visible.

### Main finding of round 1: rule 1 over-triggers on any mention of money

Three of the seven tickets tested so far mention money. All three came back `refund_request` / `hard_stop`, including one that should not have.

| Ticket | Player's actual ask | True label | Model |
|---|---|---|---|
| T033 | "I do not want the items I want the money back" | refund_request | refund_request, correct |
| T035 | "give me back my 99.99" | refund_request | refund_request, correct |
| T023 | "the event is over, what happens with my money" | refund_request (label corrected) | refund_request, correct |
| T021 | "I PAID 49.99 AND GOT NOTHING THIS IS THEFT" | **purchase_missing** | **refund_request, wrong** |

**The hypothesis.** Rule 1 fires when a ticket "reasonably belongs to more than one category". The model appears to read *any mention of money* as reasonable grounds for `refund_request`, and then correctly applies the most-restrictive rule on top of that faulty premise. The error is not in rule 1's arithmetic, it is in what counts as belonging to a category.

T021 shows it clearly. The player never asks for money back. They say they paid and received nothing, which is the definition of `purchase_missing`. The model's own `reason` field says "demand money back", which the ticket does not contain. That is two failures in one: rule 4 (tone is not signal, and THEFT is tone) and rule 5 (do not invent, and the demand was invented).

**Why this matters more than one wrong answer.** If this generalises across the 90, `purchase_missing` collapses into `refund_request` and every payment-related ticket becomes a hard stop. The taxonomy still routes safely, but it stops being useful: the whole `human_review` tier for payments disappears and nothing in that area is ever automated. An over-cautious system that hard-stops everything is not a triage system, it is an off switch.

**What NOT to do now.** Do not rewrite the prompt against these four examples. Four visible cases is not evidence of a pattern, it is a hypothesis, and tuning against examples you can see is how you build a prompt that scores well on ten tickets and badly on eighty. Run the full 90 first and see whether `purchase_missing` actually collapses.

**The fix to try in round 2, if the pattern holds.** Do not touch rule 1. Tighten the boundary inside the two category definitions instead, since definitions carry disambiguation more reliably than rules do. The distinguishing test is what the player asks for, not what they mention: `purchase_missing` is "I want what I paid for", `refund_request` is "I want my money back". Mentioning a sum, a charge, or the word theft is not an ask.

### Label corrections

Corrections to `03-tickets.csv` made during testing. Every one is recorded here with its reasoning, and the count belongs in the README. A dataset that is never corrected by contact with a model is a dataset nobody examined; a dataset corrected silently is a dataset nobody can trust.

**The discipline:** a label may be changed only when the original reading is wrong on re-reading the ticket text alone. It may never be changed because the model disagreed with it. The model disagreeing is what makes you re-read; it is not the reason.

| Ticket | Was | Now | Reasoning |
|---|---|---|---|
| T023 | purchase_missing / human_review | refund_request / hard_stop | The original note said "the ask is still delivery". Re-reading the ticket, that is wrong. The player states the event is over, so there is nothing left to deliver, and the closing line is "what happens with my money". It is a money question. The model's classification was better than the label. |

### Open finding from round 1

Rule 3 (confidence below 0.75 forces `human_review`) cannot be observed on a ticket whose category already maps to `human_review`. To know whether the rule actually works, the full run needs at least one ticket that lands on `gameplay_question` or `bug_report` with confidence under 0.75. If no such case appears naturally across the 90, the rule is untested and you should say so rather than claim it works. Cheapest fix: log the raw confidence and the pre-rule action alongside the final action, so the evaluation script can count how many times rule 3 actually changed an outcome.

## Change log

One line per change. What you changed, why, and what it fixed. Keep it short.

| # | What I changed | Why | Effect |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

**Keep prompt v1 exactly as it was.** Save it in a file before you edit anything. Showing v1 next to the final version is more convincing than showing the final version alone, and it costs you one copy-paste now and is impossible to reconstruct later.

---

## Round 1b — 60 automated runs, two models

**Date:** 2026-09-08
**Prompt:** v1, unchanged
**Method:** 60 independent runs. The same 10 tickets, on Sonnet 5 and Opus 5, three times each. One isolated agent per run with a clean context, so no run could see another's answer. Full raw results in `results_subagents.jsonl`, scored by `score_eval.py`, output in `report_subagents.md`.

**Caveat on method, and it matters:** these ran as isolated subagents, not in a chat window and not through the API. Each environment carries its own system prompt, so the numbers below describe this setup and do not transfer unchanged to either of the other two. Reproduce through the API before quoting any of it in the README.

### Headline

| | Sonnet 5 | Opus 5 | Pooled |
|---|---|---|---|
| Category accuracy | 26/30 = 86.7% | 29/30 = 96.7% | 55/60 = 91.7% |
| **Safety failures** | **0** | **0** | **0** |
| Under-routing | 0 | 0 | 0 |
| Over-routing | 4 | 1 | 5 |
| Self-consistency | 9/10 tickets unanimous | 9/10 unanimous | |

**Zero safety failures in 60 runs, on the ten hardest tickets in the set, across two models.** That is the number the whole design exists to produce.

**Every single error was over-routing. Not one under-route in 60 runs.** The system's failures are all in the direction of asking a human to look at something that did not need it. That is the trade the taxonomy was built to make, and it held under repetition rather than being a lucky draw.

### The models differ on exactly one ticket

Every category error, on both models, was T021. Nine of ten tickets were identical across all six runs of both models.

| Model | T021 outcome |
|---|---|
| Sonnet 5 | `refund_request` three times out of three. Confidence 0.85, 0.85, 0.90. Its `reason` field asserted a money-back demand the ticket does not contain, in all three runs |
| Opus 5 | `refund_request` once at confidence **0.62**, with a reason that said out loud "no explicit money-back request; ambiguous between refund and delivery". Then `purchase_missing`, correctly, twice at 0.82, citing rule 4 by name |

So the difference between the models here is not really accuracy. It is whether the model knows when it is guessing. Sonnet was confidently wrong and filled the gap with an invented fact. Opus was either unsure and said so, or right for the stated reason.

### Calibration, and an honest limit on what it shows

| Confidence claimed | Sonnet accuracy | Opus accuracy |
|---|---|---|
| below 0.75 | 0% (n=1) | 67% (n=3) |
| 0.75 to 0.89 | 94% (n=17) | 100% (n=13) |
| 0.90 and above | 83% (n=12) | 100% (n=14) |

Sonnet's table is inverted at the top: it was *less* accurate when it claimed more confidence. Opus's is ordered correctly.

**Do not over-read this.** All five errors in the whole exercise are one ticket, so every cell in Sonnet's table is really a statement about T021 and nothing else. Ten tickets cannot produce a calibration curve, and this one does not. What the data does support is narrower and still useful: on the one ticket where the two models diverged, Opus's confidence figure carried information and Sonnet's did not.

### Rule 3 is confirmed untested

The model's own action and the action computed in code differed **0 times out of 60**. The reason is structural, not encouraging: every confidence below 0.75 landed on a category that already routes to `human_review` or `hard_stop`, so the rule never had an opportunity to change anything. Confirms the round 1 finding rather than resolving it.

### A bug in rule 3 that both models quietly corrected

Rule 3 says "set the action to `human_review` regardless of category". Read literally, a `hard_stop` at confidence 0.70 becomes `human_review`, which is *less* restrictive. That is the opposite of what the rule is for.

Sonnet hit exactly this case: T046 run 3, `account_recovery` at 0.72, and it returned `hard_stop` rather than obeying the instruction. Both models ignored the literal wording in favour of the obvious intent, and the code in `run_eval.py` was written the same way, only ever downgrading `auto_draft`.

Fix in v2: "If your confidence is below 0.75, never assign `auto_draft`. Use `human_review` instead. Low confidence never makes an action less restrictive."

### What this changes about the build

**Model tiering, not model choice.** Sonnet is right on nine of ten and its errors are all over-routes, which cost human time rather than safety. Opus is right on the tenth. The sensible architecture is Sonnet by default with an escalation to Opus on low confidence or on any ticket in the payment cluster, which is the same model-tiering pattern already running in Gravity Guard. Cheaper than Opus everywhere and better than Sonnet alone.

**The purchase_missing / refund_request boundary is the one real defect.** Confirmed across 60 runs. Fix it in the category definitions in v2, not in rule 1.

**Is the procedure worth keeping?** Yes, on this evidence. Ten tickets chosen to be hard, run repeatedly, found a reproducible classification defect, a wording bug in a rule, an untestable rule, and a concrete model-tiering decision. None of that would have surfaced from a single pass over 90 tickets reporting one accuracy figure.

---

## Zendesk integration, 2026-09-09

Trial opened, 90 tickets seeded, all 90 annotated from the stored classifications without calling a model again. **Zero routing mismatches against the ground truth: 90 of 90.**

| Action | Tickets in the queue |
|---|---|
| hard_stop | 36 |
| auto_draft | 29 |
| human_review | 25 |

### API tokens were not available, so the project runs on OAuth

Zendesk is retiring API tokens (they stop working 30 April 2027) and the trial account offered no way to create one. Rather than switch platforms, the project authenticates through the OAuth 2.0 authorization code flow: a confidential client registered in Admin Center, a one-time browser consent caught by a local server on `localhost:8080`, and a bearer token from then on. `zendesk_oauth.py` runs that once; `zendesk_client.py` prefers the bearer token and keeps API-token auth only as a fallback.

This turned out better than the original plan. Building on the path Zendesk is moving to is a stronger thing to have done than building on the one it is closing, and the state parameter and confidential-client choice are worth explaining in an interview.

### Two silent failures in one day

**The domain rejection.** Ticket requesters need an email address, and for 90 synthetic players I invented them under `example-synthetic.invalid`. `.invalid` is reserved by RFC 2606 precisely so it can never be registered or receive mail, which makes it the standards-correct choice. Zendesk rejected all 90: it validates the top-level domain against a list of real ones rather than against the standard. Switching to `example.com`, reserved by the same RFC but under a real TLD, fixed it.

Worth keeping as a small, exact example of the gap between what is correct by specification and what a real platform accepts.

**The one that mattered more, and it was mine.** The seeding script polled the bulk-create job, saw `status: completed` and `progress: 90/90`, and printed "done. 90 processed." Every one of the 90 had failed. Zendesk's job status carries a per-item `results` array with an error on each failed entry, and the script never looked at it. Processed is not succeeded.

The failure only surfaced because the mapping step afterwards came back empty and got investigated instead of shrugged at.

**This is the second silent failure in a single day.** The first was `score_eval.py` reporting a confident 98.9% over 87 tickets while the operator believed it had covered 90. Two of these in one day is a pattern, not coincidence, and the pattern is the same each time: a script reporting success on a stage it never actually verified.

Both are now fixed the same way, by checking the thing itself rather than the status of the thing:

- `score_eval.py` prints per-model coverage against the ground truth before any figure, and says loudly when a model is missing tickets.
- `seed_tickets.py` reads the job's `results` array, counts failures, and prints the first few with their reasons.
- `backfill_zendesk.py` skips tickets already carrying `ai_triaged`, so an interrupted run resumes instead of adding a second internal note.

This belongs in the README. An evaluation harness that can report success on work it did not do is worse than no harness, and finding two of them by accident is the argument for building the check into every stage rather than trusting a status field.

### Rate limiting behaved as designed

The backfill hit a 429 partway through. The client read `Retry-After`, waited 22 seconds and continued without losing a ticket. Written before it was needed, which is the only time that code is cheap to write.

---

## Round 3 — both models, all 90 tickets, one pass each

**Date:** 2026-09-09
**Prompt:** v1, unchanged
**Models:** claude-sonnet-5 and claude-opus-5 via the Anthropic API
**Design:** 90 tickets, one pass per model, 180 responses. Symmetric, no weighting.
**Raw:** `results_raw.jsonl`

### Results

| | Sonnet 5 | Opus 5 |
|---|---|---|
| Category accuracy | 89/90 = 98.9% | 89/90 = 98.9% |
| **Action correct** | **90/90 = 100%** | 89/90 = 98.9% |
| Safety failures | 0 | 0 |
| Under-routing | 0 | 0 |
| Over-routing | 0 | 1 |
| Input tokens | 80,734 | 80,734 |
| Output tokens | 9,616 | 16,107 |

Identical input cost, Opus generating 1.7x the output, and no accuracy to show for it. On routing, the metric the system actually exists to get right, Sonnet was perfect and Opus was not.

### The expensive model did not win, and the ten-ticket test said it would

Round 1b, on ten hand-picked hard tickets in a subagent environment, put Opus at 96.7% and Sonnet at 86.7%. On the full set the gap is gone and the sign is reversed.

Both measurements were correct about what they measured. Edge-case testing tells you where the ceiling is. Full-set testing tells you what the queue will actually experience. A real support queue is mostly easy tickets, so the full-set number is the one that decides the architecture and the edge-case number is the one that tells you where to be careful.

**Decision: Sonnet 5.** Recorded here with the evidence, because "I used the cheaper model and here is the measurement that justified it" is a different sentence from "I used the cheaper model".

### The finding: the two models never made the same mistake

| Ticket | Truth | Sonnet | Opus |
|---|---|---|---|
| T050 | progress_lost | progress_lost (0.80) correct | account_recovery (0.70) **wrong** |
| T077 | bug_report | gameplay_question (0.80) **wrong** | bug_report (0.79) correct |

Those two tickets are the only two in ninety where the models disagree, **and they are exactly the two errors**. Zero overlapping errors. Zero disagreements on tickets both got right.

On this set, cross-model disagreement detected 100% of errors with no false alarms.

**The caveat, stated plainly:** that is two errors. "Caught 2 of 2" is a mechanism worth noticing, not a statistic worth quoting. Anyone who reports 100% error detection off two data points is telling you they do not understand the number.

### Why the mechanism still matters: Sonnet has no uncertainty signal

| Confidence | Sonnet responses | Opus responses |
|---|---|---|
| below 0.75 | **0** | 4 |
| 0.75 to 0.89 | 37 (97.3% accurate) | 34 (100%) |
| 0.90 and above | 53 (100%) | 52 (100%) |

Sonnet never went below 0.75 in ninety responses. Not once. So a confidence-threshold escalation is unavailable with Sonnet: the trigger never fires. This kills the round 1b plan of "Sonnet by default, escalate to Opus on low confidence", because Sonnet will never report low confidence.

Opus, by contrast, flagged its own single error at 0.70. Its confidence carries real information.

That is the actual difference between the two models on this task. Not accuracy. Whether the model tells you when it is unsure.

### But the ensemble does not pay, and this is the useful part

The tempting conclusion is to run both models and send disagreements to a human. Measured:

| Configuration | Action accuracy | Cost |
|---|---|---|
| Sonnet alone | **90/90** | 1x |
| Both, disagreement to human_review | 89/90 | ~2x |

The ensemble is **worse**. T050's true action is `human_review`, so routing it there is right, but T077's true action is `auto_draft`, so sending it to a human is an over-route Sonnet did not make. Two models, twice the cost, one more mistake.

**Sonnet alone wins, and testing the clever architecture and reporting that it lost is worth more than shipping it.**

### Where the disagreement signal does belong

Not in the routing path. In quality assurance.

Run both models over a sample periodically, offline, and treat every disagreement as a ticket for a human to review. On this set that would have surfaced both hard cases and nothing else, which is exactly what a QA sampling process wants: high yield, no noise. It costs nothing at request time because it does not run at request time.

Disagreement is a detector, not a router. Keeping those separate is the whole point.

### Rule 3 finally fired, and it did damage

`Rule 3: the model's own action differed from the action computed in code 1 times out of 90.`

That one time was T050. Opus classified it `account_recovery`, which maps to `hard_stop`, then obeyed rule 3 literally at confidence 0.70 and downgraded its own action to `human_review`. Low confidence made the system **less** protective, which is precisely the wording bug identified in round 1b.

The code caught it and restored `hard_stop`.

This is the concrete demonstration that deterministic rules belong in code rather than in a prompt. Not an argument, an incident: a model followed a badly worded instruction correctly and weakened a safety control, and a five-line function prevented it. Put this in the README.

### Process failure worth recording

The first Opus run printed 90 tickets and reported zero failures, but only 87 records reached the file. T001 to T003 were never written and no error was raised. The cause was never established.

The evaluation script computed a confident 98.9% over 87 tickets while the operator believed it had run 90. That is the failure mode that quietly invalidates evaluations, and the only reason it was caught was a manual count of the confusion matrix.

**Fix applied:** `score_eval.py` now prints coverage per model before any figure and states loudly when a model does not cover every ticket in the ground truth. An evaluation that silently reports on a subset is worse than one that refuses to report.

### Standing after round 3

- **Zero safety failures across 315 responses**, two models, two environments, three rounds.
- Sonnet 5, prompt v1: 90/90 correct routing on the full set.
- Model choice settled, with evidence.
- Rule 3's wording bug demonstrated live rather than argued.
- Still untested: the drafting prompt, and repeat runs across the full set.

---

## Round 2 — first full pass, 90 tickets, via the API

**Date:** 2026-09-09
**Prompt:** v1, unchanged
**Model:** claude-sonnet-5 via the Anthropic API, run by Erez in VS Code
**Raw:** `results_raw.jsonl`

### Read the report with these two corrections

**The Opus figure is not comparable.** Opus has 25 responses covering only the 10 sample tickets, because that run was interrupted. Sonnet has 110 covering all 90. Putting "Opus 100%" beside "Sonnet 97.3%" invites a false conclusion. Only the Sonnet table can be quoted, and only as what it is.

**The pooled table is weighted.** The 10 hand-picked hard tickets appear three times each, the other 80 once. That biases the pooled figure downward, which is the safe direction, but it is still not a clean number. Do not put the pooled figure in the README.

### The honest headline

Across **110 Sonnet responses covering all 90 tickets**, prompt v1:

| Metric | Result |
|---|---|
| Category errors | 3, on three distinct tickets |
| **Safety failures** | **0** |
| Under-routing | 0 |
| Over-routing | 1 |

Zero safety failures now stands at 135 responses across two models and two environments.

### The round 1 hypothesis was wrong

Round 1 proposed that rule 1 over-triggers on any mention of money, and that `purchase_missing` would collapse into `refund_request` across the full set. **It did not.** Thirteen of the fourteen `purchase_missing` tickets classified correctly.

The hypothesis was built on one ticket in one environment. This is exactly why the round 1 note said not to rewrite the prompt against ten visible examples, and it is the single most useful thing this round produced. Had the prompt been "fixed" yesterday, it would have been fixed against noise.

### The environment changes the answer

T021 failed 3 out of 3 as a subagent, at confidence 0.85 to 0.90, with a fabricated claim in its reason field. Through the API it classified correctly. Same prompt, same model, opposite result.

Consequence for this project: results do not transfer between environments, and the environment belongs beside every figure quoted, alongside the model and the prompt version. Consequence more generally: "I tested my agent" means nothing without saying where.

### The three errors, and why two were mine

| Ticket | Model said | Label said | Verdict |
|---|---|---|---|
| T024 | progress_lost | purchase_missing | **Label was wrong.** The coins arrived and then vanished, so the purchase was delivered and later lost. That is `progress_lost` by this project's own definition. Corrected |
| T018 | refund_request | purchase_missing | **Label was wrong.** A double charge spans both categories, and rule 1 says the most restrictive wins. The label contradicted the project's own rule. Corrected |
| T077 | gameplay_question | bug_report | **Genuine disagreement, label kept.** The app changed its own language, which is a fault; the player's ask is where the setting is. Both readings hold, both route to `auto_draft`, so there is no routing consequence. Recorded in the CSV as a known disagreement |

### THE LABELS ARE NOW FROZEN

Three corrections in one dataset (T023, T024, T018) is the limit of what can be defended. Past that point the ground truth is being fitted to the model and every number in the report loses meaning.

**From here: no label changes.** If a label later looks wrong, leave it and record the disagreement separately, the way T077 was handled. The README states that three labels were corrected during testing, with the reasoning, and that the set was frozen afterwards. Disclosing it is what makes the rest believable.

### Calibration, now on real evidence

| Confidence | Responses | Actual accuracy |
|---|---|---|
| below 0.75 | 0 | n/a |
| 0.75 to 0.89 | 49 | 93.9% |
| 0.90 and above | 61 | 100.0% |

Correctly ordered, on 110 responses. Yesterday's inverted table was one ticket's noise, and this supersedes it. The confidence figure carries real ordinal information in this environment.

### Rule 3 is confirmed dead

**Zero of 110 responses came back below 0.75.** With this prompt, in this environment, Sonnet never enters the range the rule governs. The threshold protects nothing.

Options: drop rule 3 and say so; keep it and state in the README that it never fired; or raise the threshold to somewhere it would actually bite, around 0.85, and measure what that costs in over-routing. The last is the interesting one and the evaluation script already supports it: `python3 score_eval.py --threshold 0.85`.

### What is still not known

- Opus on the full 90. Only ten tickets so far.
- Whether the three-run spread holds on the full set. Only one pass per ticket for most of them.
- Whether the drafting prompt works at all. Never exercised.

---

## Round 2 — after the code exists

Do not fill this in tonight. This is where the evaluation script's output goes: overall accuracy, per-category accuracy, the three error counts from section 7.1 of the build spec, and the confidence threshold you settled on and why.
