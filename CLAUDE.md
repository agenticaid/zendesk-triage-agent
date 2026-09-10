# Project context

Support ticket triage agent. A three-day portfolio build, not a product.

Read `docs/00-BUILD-SPEC.md` before proposing any work. The out-of-scope list in section 4 is binding: no RAG, no multi-turn, no UI, no Hebrew, no real data, no fine-tuning. If a change would add something on that list, say so instead of building it.

## What this is

Zendesk trial instance seeded with the 90 synthetic tickets in `data/03-tickets.csv`. A Python service classifies each ticket into one of seven categories and assigns one of three actions. A native Zendesk trigger + webhook orchestrates: it watches Zendesk for new tickets, calls the service, and writes a tag plus an internal note back to the ticket.

Hosting is Google Cloud Run, chosen for its Always Free tier and because it matches the target architecture of Erez's Enosh project. Not Railway (credit exhausted), not Render (cold starts break the webhook).

Orchestration is a native Zendesk trigger + webhook calling the Cloud Run service directly on ticket creation, not Make. Make was the original plan and is still worth naming in the README as a considered-and-rejected option: it would only have been there to relay a "new ticket" event, work Zendesk already does natively via Triggers + Webhooks, so adding it would have been an unnecessary layer. Do not move classification logic into either Zendesk or a no-code tool: it must live in version-controlled Python (`main.py`).

## Current state (as of 2026-09-10)

- Both prompts have been exercised end to end. `prompt_classify_v1` classified all 90
  tickets (round 2, see `docs/06-PROMPT-LOG.md`). `prompt_draft_v1` has now drafted and
  posted all 29 `auto_draft` tickets to the trial Zendesk instance as internal notes.
- `prompts/prompt_draft_v1.txt` carries one line beyond the version frozen in
  `docs/07-PROMPT-VERSIONS.md`: a rule against attaching a specific number, threshold, or
  timeframe to a policy the model can't verify for this game. Added after review
  caught it inventing an account-deletion timeframe (ticket T066).
  `docs/07-PROMPT-VERSIONS.md` has not been updated to record this yet.
- Open, undecided: T057's drafted reply still opens with a confident, unhedged claim
  about a game mechanic ("that's a rule rather than a bug") before it hedges. It
  doesn't break any of the three non-negotiable rules below, so it shipped, but it's
  a different failure mode than T066 and the current prompt doesn't guard against it.
  Needs either a second guardrail line or a deliberate decision to accept it as
  within tolerance, the way T077 was recorded as a disagreement rather than fixed.
- This project's working copy lives only on this machine, in this folder. A Claude
  session needs this folder connected, with `.env` present, to do anything beyond
  reading the `.md` files. Mid-build, a cloud session's own workspace copy of the
  generated files (`data/results_raw.jsonl`, `data/drafts.jsonl`, `data/zendesk_ticket_map.json`)
  and `.env` went missing with no established cause. If a session reports those
  files are missing, check the folder connection before assuming the project
  regressed.

## Non-negotiable rules

- Three categories are hard-stopped and must never receive a drafted reply: `account_recovery`, `refund_request`, `abuse_report`. The reasoning is in `docs/02-TAXONOMY-AND-GUARDRAILS.md`. Do not relax this for convenience, test coverage, or a demo.
- No drafted reply is ever posted as a public Zendesk comment. Drafts go in internal notes only (`"public": false`).
- When a ticket spans two categories, the most restrictive action wins.
- Confidence below the threshold downgrades the action to `human_review`, never upgrades it.
- Zendesk credentials live in environment variables. `.env` is gitignored. Never write a token into a file in this repo.

## Conventions

- Tags written back to Zendesk: `ai_cat_<category>`, `ai_action_<action>`, plus `ai_triaged`.
- Ground truth lives only in `data/03-tickets.csv`. The agent never reads that file at classification time.
- Keep the classification prompt and the drafting prompt in separate files, matching `docs/04-AGENT-PROMPT.md`.
- One file per job: seeding, triage, evaluation. Do not build a framework.
- Suggested-reply internal notes (`note_for()` in `scripts/draft_replies.py`) carry nothing but one instruction line and the draft itself, no fences, no repeated metadata, so an agent can select-to-end and paste straight into the public reply. Category, confidence, and model already live on the separate TRIAGE AGENT note from `scripts/backfill_zendesk.py`; don't duplicate them here.

## Zendesk API notes

- Auth is HTTP Basic with username `<email>/token` and the API token as password.
- Sending `tags` on a ticket update replaces the full tag list. Use `PUT /tickets/{id}/tags.json` to append.
- `create_many` is asynchronous and returns a job status, not tickets.
- Handle `429` by reading `Retry-After` and sleeping.

## Definition of done

Section 7 of `docs/00-BUILD-SPEC.md`. Six items, all required. The third one, zero hard-stop tickets receiving an auto-draft, is pass or fail.
