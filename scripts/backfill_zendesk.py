#!/usr/bin/env python3
"""
backfill_zendesk.py - write the stored classifications onto the seeded tickets.

The 90 classifications already exist in results_raw.jsonl. This applies them as
tags and internal notes without calling any model again, so the whole queue is
triaged in a couple of minutes and there is something to screenshot before any
of the live plumbing exists.

It also isolates two questions that are painful to debug together: does the
logic work against Zendesk, and does the trigger plumbing work. This answers
the first one on its own.

Usage (from repo root):
    python3 scripts/backfill_zendesk.py --dry-run
    python3 scripts/backfill_zendesk.py
    python3 scripts/backfill_zendesk.py --model claude-opus-5

No drafted reply is ever posted as a public comment. Every comment this writes
is internal.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zendesk_client import Zendesk

HERE = Path(__file__).parent
RESULTS = HERE.parent / "data" / "results_raw.jsonl"
TICKETS = HERE.parent / "data" / "03-tickets.csv"
MAP_FILE = HERE.parent / "data" / "zendesk_ticket_map.json"

ACTION_BY_CATEGORY = {
    "gameplay_question": "auto_draft",
    "bug_report": "auto_draft",
    "purchase_missing": "human_review",
    "progress_lost": "human_review",
    "account_recovery": "hard_stop",
    "refund_request": "hard_stop",
    "abuse_report": "hard_stop",
}

CONFIDENCE_THRESHOLD = 0.75

# Why each hard-stopped category is refused. This text is the point of the whole
# project, so it goes on the ticket where a reviewer actually sees it.
REFUSAL = {
    "account_recovery":
        "NOT AUTOMATED. Account recovery is identity verification. Every account takeover "
        "begins with someone convincingly claiming to be the account owner, and a model "
        "optimised to be helpful is the wrong thing to place in that conversation. This is "
        "not an accuracy threshold that can be met; the category is excluded by policy.",
    "refund_request":
        "NOT AUTOMATED. Money. Consumer-protection rules vary by market and app store, and "
        "where a minor's spending is involved there is a legal dimension. No automated reply "
        "about reversing a charge is safe.",
    "abuse_report":
        "NOT AUTOMATED. Player safety, and a duty of care where minors are involved. Reports "
        "are also frequently retaliatory or false, which needs judgement this system does not "
        "have.",
}

REVIEW_REASON = {
    "purchase_missing":
        "Held for human review: the claim needs a receipt checked against the transaction log "
        "and cannot be evaluated from ticket text alone.",
    "progress_lost":
        "Held for human review: frequently the same underlying situation as an account problem, "
        "described differently. Confirm which account the player is signed into before promising "
        "any restoration.",
}


def computed_action(category, confidence):
    action = ACTION_BY_CATEGORY.get(category)
    if action is None:
        return None
    try:
        if float(confidence) < CONFIDENCE_THRESHOLD and action == "auto_draft":
            return "human_review"
    except (TypeError, ValueError):
        return "human_review"
    return action


def build_note(rec, action, truth_row):
    cat = rec["category"]
    conf = rec.get("confidence")
    lines = [
        "TRIAGE AGENT",
        f"Category: {cat}",
        f"Action: {action}",
        f"Confidence: {conf}",
    ]
    if rec.get("secondary_category"):
        lines.append(f"Also reads as: {rec['secondary_category']}")
    lines.append("")
    if rec.get("reason"):
        lines.append(rec["reason"])
        lines.append("")

    if action == "hard_stop":
        lines.append(REFUSAL.get(cat, "NOT AUTOMATED."))
    elif action == "human_review":
        lines.append(REVIEW_REASON.get(cat, "Held for human review."))
        if ACTION_BY_CATEGORY.get(cat) == "auto_draft":
            lines.append(f"(Downgraded from auto_draft: confidence below {CONFIDENCE_THRESHOLD}.)")
    else:
        lines.append("Eligible for a drafted reply. A human reviews and sends it; "
                     "nothing is sent automatically.")

    lines += ["", "---",
              f"Synthetic ticket {truth_row['id']} | model {rec['model']} | prompt v1 | "
              "classification only, no reply generated"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="re-annotate tickets already tagged ai_triaged")
    args = ap.parse_args()

    if not MAP_FILE.exists():
        raise SystemExit("data/zendesk_ticket_map.json not found. Run scripts/seed_tickets.py first.")
    mapping = json.loads(MAP_FILE.read_text(encoding="utf-8"))

    with TICKETS.open(encoding="utf-8") as f:
        truth = {r["id"]: r for r in csv.DictReader(f)}

    picked = {}
    with RESULTS.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("model") == args.model and r.get("category") and not r.get("error"):
                picked.setdefault(r["ticket_id"], r)   # first clean run wins

    print(f"{len(picked)} classifications from {args.model}")
    print(f"{len(mapping)} tickets mapped in Zendesk")

    todo = [tid for tid in sorted(mapping) if tid in picked]
    skipped = sorted(set(mapping) - set(picked))
    if skipped:
        print(f"No classification for {len(skipped)}: {', '.join(skipped[:10])}")

    counts = {"auto_draft": 0, "human_review": 0, "hard_stop": 0}
    zd = None if args.dry_run else Zendesk()

    # Adding a second internal note to a ticket that already has one is ugly, and
    # is exactly what an interrupted run would do, so skip anything already tagged.
    if zd and not args.force:
        already = {t["external_id"] for t in zd.list_tickets()
                   if t.get("external_id") and "ai_triaged" in (t.get("tags") or [])}
        if already:
            print(f"{len(already)} tickets already annotated, skipping them. --force to redo.")
            todo = [t for t in todo if t not in already]

    # Adding a second internal note to a ticket that already has one is ugly and
    # is exactly what an interrupted run would do, so skip anything already tagged.
    if zd and not args.force:
        already = {t["external_id"] for t in zd.list_tickets()
                   if t.get("external_id") and "ai_triaged" in (t.get("tags") or [])}
        if already:
            print(f"{len(already)} tickets already annotated, skipping them. --force to redo.")
            todo = [t for t in todo if t not in already]

    for n, tid in enumerate(todo, 1):
        rec = picked[tid]
        action = computed_action(rec["category"], rec.get("confidence"))
        counts[action] += 1
        tags = ["seed", "synthetic", "ai_triaged",
                f"ai_cat_{rec['category']}", f"ai_action_{action}"]
        note = build_note(rec, action, truth[tid])

        if args.dry_run:
            if n <= 2 or action == "hard_stop" and n < 6:
                print(f"\n--- {tid} -> Zendesk #{mapping[tid]} ---")
                print("tags:", tags)
                print(note)
            continue

        zd.update_ticket(mapping[tid], tags=tags, internal_note=note)
        print(f"  {n}/{len(todo)} {tid} -> #{mapping[tid]} | {rec['category']} / {action}")

    print("\nRouting distribution:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    if args.dry_run:
        print("\nDry run. Nothing was written. Drop --dry-run to apply.")
    else:
        print(f"\n{len(todo)} tickets tagged and annotated. Open the Zendesk agent view "
              "and take the screenshots now, before the trial expires.")


if __name__ == "__main__":
    main()
