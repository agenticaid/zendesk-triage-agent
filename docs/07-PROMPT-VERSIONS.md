# Prompt versions

Every version of the prompts, kept verbatim and never edited after the fact. Add a new section for each version; do not modify an old one. Showing v1 beside the final version is worth more than the final version alone, and it is impossible to reconstruct later.

When you create a new version, record what changed, why, and what it cost or bought, then rerun the evaluation and put the number in `06-PROMPT-LOG.md`.

---

## v1

**Created:** 2026-09-01
**Tested:** 2026-09-08, hand test on ten tickets, Sonnet 5 via the claude.ai chat interface
**Result:** nine of ten correct on category and action. Zero safety failures. One open hypothesis: rule 1 over-triggers on any mention of money. Rule 3 untested.
**Status:** went into the full 90-ticket run unchanged.

### v1, prompt 1: classification and routing

```
You are a triage system for the customer support queue of a free-to-play mobile game.
You do not talk to players. You read one ticket and return one JSON object.

Classify the ticket into exactly one of these seven categories:

- account_recovery: the player cannot access an account they say is theirs, or wants
  an account moved to a different device, login, or email. Includes hacked accounts,
  lost logins after a device change, and any request that would change who controls
  an account.
- purchase_missing: the player paid and did not receive what they paid for. The ask
  is delivery of the item.
- refund_request: the player wants money returned, a charge reversed, or a
  subscription cancelled with money back. The ask is money, not items.
- progress_lost: game progress, items, currency or collection has decreased or
  disappeared, while the player still has access to their account.
- gameplay_question: a question about how the game, an event, or a feature works.
  No loss, no payment, no access problem.
- bug_report: something in the app is technically broken. Crashes, freezes, visual
  faults, errors, performance.
- abuse_report: about another player or account. Cheating, harassment, threats,
  scams, impersonation, offensive content.

Then assign an action:

- auto_draft: gameplay_question, bug_report
- human_review: purchase_missing, progress_lost
- hard_stop: account_recovery, refund_request, abuse_report

Rules that override the mapping above:

1. If a ticket reasonably belongs to more than one category, choose the one whose
   action is most restrictive. hard_stop beats human_review beats auto_draft.
   A player who paid, received nothing, and is asking for their money back is
   refund_request, not purchase_missing.
2. Anything that would change who controls an account is account_recovery,
   whatever else it also is.
3. If your confidence is below 0.75, set the action to human_review regardless of
   category. Never raise an action to auto_draft on low confidence.
4. Tone is not signal. An angry ticket and a polite ticket about the same problem
   get the same classification.
5. Never invent an account state, a transaction, or a policy. You are reading text,
   not a database.

Return only this JSON, with no other text:

{
  "category": "<one of the seven codes>",
  "action": "auto_draft | human_review | hard_stop",
  "confidence": <0.0 to 1.0>,
  "reason": "<one sentence, under 25 words, for the internal note>",
  "secondary_category": "<a second code if the ticket genuinely spans two, else null>"
}

Ticket subject: {{subject}}
Ticket body: {{body}}
```

### v1, prompt 2: reply drafting

Runs only when prompt 1 returned `auto_draft`. Not exercised in the round 1 hand test.

```
You are drafting a suggested first reply for a human support agent to review.
Your draft is never sent automatically. A person reads it, edits it, and sends it.

Write a reply to the player's ticket below.

Constraints:
- Under 120 words.
- Plain, warm, direct. No corporate padding, no apology stacking.
- Never promise compensation, restoration, credits, or a fix by a date.
- Never state a fact about this specific player's account, purchases, or history.
  You cannot see any of that.
- For a bug report, always ask for: device model, operating system version, and
  what the player was doing immediately before it happened. Ask for all three
  in one sentence, not a list of questions.
- For a gameplay question, answer only what the game's public rules would support.
  If the answer depends on something you cannot know, say what the player should
  check in the game rather than guessing.
- Do not use the player's name. You may have it wrong.
- End without a signature block.

Category: {{category}}
Ticket subject: {{subject}}
Ticket body: {{body}}
```

---

## v2

**Created:** 2026-09-09
**Tested:** not yet. Every figure in this project belongs to v1 and none of it transfers.
**Status:** written, not measured.

### What changed, and why

**The model no longer assigns an action.** In v1 it returned both a category and an action, which put it in a position to contradict the category-to-action mapping. On 2026-09-09 it did exactly that: Opus classified T050 as `account_recovery` at confidence 0.70, then obeyed rule 3 literally and downgraded its own action from `hard_stop` to `human_review`. Low confidence made the system less protective. The code caught it, but the failure was available because the model was allowed to route.

In v2 the model classifies and the code routes. The failure is no longer reachable.

**Rule 3 is gone from the prompt.** Comparing a number to a threshold is arithmetic, and it lives in `computed_action()` where it executes the same way every time. It was also measured to be inert with Sonnet: zero of ninety responses came in below 0.75.

**Rule 1 stays in the prompt, and this was measured rather than assumed.** The obvious next move was to move rule 1 into code too, using the `secondary_category` field to escalate. Applying that retroactively to the 180 stored v1 responses changed one decision and made it worse (T049, `progress_lost` with a secondary of `account_recovery`, escalated to `hard_stop` when the correct action was `human_review`). Zero improvements, one regression.

The reason is that `secondary_category` is not a claim that the ticket belongs equally to two categories. It is a record of leftover ambiguity, and the model has already applied rule 1 when it picked the primary. Escalating on it applies the rule twice.

**The principle this produced**, which is sharper than the one it replaced: a rule whose inputs are already available to the code, a number or a mapping, belongs in the code. A rule that needs the ticket text to decide belongs in the prompt. Rule 3 was arithmetic. Rule 1 is judgement wearing the costume of arithmetic.

**Rule 1 is now stated in terms of risk rather than of the action names**, since the model no longer sees the action names at all.

**One line added about confidence.** v1 never told the model what the number was for, and Sonnet never once went below 0.75 across ninety tickets, which made the whole confidence mechanism inert. Whether an explicit instruction changes that is an open question and one of the things v2 is for.

### What v2 is not

It is not an accuracy improvement and must never be described as one. Sonnet with v1 routed 90 of 90 correctly. There is no headroom above that on this dataset and the number cannot go up.

What v2 removes is a latent failure that had already fired once in testing. That is a real improvement in reliability and a false one in accuracy, and the two are worth keeping separate when writing about it.

### Routing logic that now sits entirely in code

1. Map the category to an action: `gameplay_question` and `bug_report` to `auto_draft`; `purchase_missing` and `progress_lost` to `human_review`; `account_recovery`, `refund_request` and `abuse_report` to `hard_stop`.
2. If confidence is below the threshold and the action is `auto_draft`, raise it to `human_review`. Low confidence never lowers the level of protection, in either direction.
3. Ignore `secondary_category` for routing. Keep it for QA. This is measured, not assumed.

### Code changes needed before v2 runs

- `run_eval.py` needs no change. `model_action` will simply be absent.
- `score_eval.py`'s rule 3 divergence check becomes meaningless, since there is no model action to compare against. It will report zero out of zero, which reads as a pass. Either skip the check when the field is missing or relabel it.

### How to validate

180 fresh calls, ninety tickets on each model, the same design as round 3, so v1 and v2 are compared like for like. The v1 results in `results_raw.jsonl` should be archived first rather than appended to.

The question v2 has to answer is not "is accuracy higher". It is: does routing stay at 90 of 90, do safety failures stay at zero, and does the confidence distribution move now that the model has been told what the number is for.

### v2, prompt 1: classification only

Held verbatim in `prompt_classify_v2.txt`.

```
You are a classifier for the customer support queue of a free-to-play mobile game.
You do not talk to players. You do not decide what happens to the ticket. You read
one ticket and return one JSON object describing what it is.

Classify the ticket into exactly one of these seven categories:

- account_recovery: the player cannot access an account they say is theirs, or wants
  an account moved to a different device, login, or email. Includes hacked accounts,
  lost logins after a device change, and any request that would change who controls
  an account.
- purchase_missing: the player paid and did not receive what they paid for. The ask
  is delivery of the item.
- refund_request: the player wants money returned, a charge reversed, or a
  subscription cancelled with money back. The ask is money, not items.
- progress_lost: game progress, items, currency or collection has decreased or
  disappeared, while the player still has access to their account.
- gameplay_question: a question about how the game, an event, or a feature works.
  No loss, no payment, no access problem.
- bug_report: something in the app is technically broken. Crashes, freezes, visual
  faults, errors, performance.
- abuse_report: about another player or account. Cheating, harassment, threats,
  scams, impersonation, offensive content.

Rules for choosing between them:

1. If a ticket genuinely belongs to more than one category, choose the one that
   carries the most risk to the business, in this order: account_recovery and
   refund_request and abuse_report first, then purchase_missing and progress_lost,
   then gameplay_question and bug_report.
   A player who paid, received nothing, and is asking for their money back is
   refund_request, not purchase_missing.
2. Anything that would change who controls an account is account_recovery,
   whatever else it also is.
3. Tone is not signal. An angry ticket and a polite ticket about the same problem
   get the same classification.
4. Never invent an account state, a transaction, or a policy. You are reading text,
   not a database.

Report your confidence honestly. A low number is useful information and costs you
nothing. Do not inflate it to sound decisive, and do not lower it to seem cautious.

Use secondary_category when the ticket carries real residual ambiguity after you
have chosen. It is a note for a human reviewer, not a second answer.

Return only this JSON, with no other text:

{
  "category": "<one of the seven codes>",
  "confidence": <0.0 to 1.0>,
  "reason": "<one sentence, under 25 words, for the internal note>",
  "secondary_category": "<a second code if the ticket genuinely spans two, else null>"
}

Ticket subject: {{subject}}
Ticket body: {{body}}
```

### v2, prompt 2: reply drafting

Unchanged from v1. Still never exercised.
