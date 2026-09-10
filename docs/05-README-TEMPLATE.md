# README template

This is the artifact a hiring manager actually reads. Fill the blanks on Day 3 and delete this line and the next. Keep it to one screen; everything below fits.

---

# Support Ticket Triage Agent

A triage system for a mobile game support queue. It reads an incoming Zendesk ticket, classifies it into one of seven categories, and routes it by risk: low-risk categories get a drafted reply for an agent to review, ambiguous ones are flagged for a human, and three categories are refused outright.

**All data here is synthetic.** 90 tickets written to resemble a free-to-play mobile game queue. There are no real players, no real purchases, and no real support organisation behind this. It was built in three days as a working demonstration.

## What it does

[one short paragraph, plain language]

## Architecture

```
Zendesk --> Make --> classification service (Cloud Run) --> Claude API
                          |
                          v
                  Make writes back tag + internal note
```

[two or three sentences on why Make is in the loop rather than direct API calls]

## The routing policy

| Category | Action | Why |
|---|---|---|
| gameplay_question | Draft a reply | Public information, no account or money exposure |
| bug_report | Draft a reply | Highly templated first response, highest volume, lowest risk |
| progress_lost | Human review | Frequently an account problem in disguise |
| purchase_missing | Human review | The claim cannot be verified from ticket text |
| refund_request | **Refused** | Money, consumer protection, and sometimes a minor's spending |
| account_recovery | **Refused** | Identity verification. This is the account-takeover surface |
| abuse_report | **Refused** | Player safety, and frequently retaliatory or false |

Three of seven categories are deliberately not automated. The reasoning is in [`02-TAXONOMY-AND-GUARDRAILS.md`](...).

The short version for account recovery: every account takeover starts with someone convincingly claiming to be the account owner, and a model tuned to be helpful is the wrong thing to put in that conversation. This is not a prompt quality problem. It is a category that should not be automated at any accuracy level.

## Results

Measured against the ground-truth labels in `03-tickets.csv`.

| Metric | Result |
|---|---|
| Tickets processed | 90 |
| Classification accuracy | __% |
| Safety failures (hard-stop tickets that received an auto-draft) | **0** (pass/fail, not a percentage) |
| Under-routing (assigned action less restrictive than true action) | __ |
| Over-routing (assigned action more restrictive than true action) | __ |
| Tickets routed to human review by the confidence threshold | __ |
| Confidence threshold used | __ |

[confusion matrix image]

### Where it gets things wrong

[This is the most valuable section in the README. Two or three sentences naming the specific confusions, for example progress_lost against account_recovery. Anyone can report a number. Explaining the error structure is what shows you looked.]

## What this is not

- Not deployed, not in production, and it has no users.
- No knowledge base or retrieval. Classification and drafting from ticket text alone.
- No drafted reply is ever sent to anyone. A human presses send.
- Single turn. It does not hold a conversation.
- English only.

## Running it

[env vars, the three commands]

## Notes

Built on a 14-day Zendesk trial, so the instance no longer exists. Screenshots in `/docs`.

---

## Reminders while you fill this in

- The "What this is not" section is not modesty, it is the section that makes the rest of the document believable. Do not trim it.
- Never write deflection rate, CSAT, cost saving, or production anywhere in this file.
- Put the word synthetic in the first paragraph, not in a footnote.
- If the accuracy number is lower than you hoped, publish it anyway and write a better error analysis. That trade is strongly in your favour.
