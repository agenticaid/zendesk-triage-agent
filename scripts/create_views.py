#!/usr/bin/env python3
"""
create_views.py - build the agent-facing views over the triaged queue.

Tags on a ticket are invisible until someone opens it. A view is the saved
filter an agent actually stares at all day, and it is the only place the
triage becomes visible as a queue rather than as metadata.

Creates four views:
    1. Refused by triage agent   tag ai_action_hard_stop
    2. Held for human review     tag ai_action_human_review
    3. Ready to draft            tag ai_action_auto_draft
    4. Not yet triaged           has the seed tag, lacks ai_triaged

Usage (from repo root):
    python3 scripts/create_views.py --dry-run
    python3 scripts/create_views.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zendesk_client import Zendesk

VIEWS = [
    {
        "title": "1. Refused by triage agent",
        "description": "Account recovery, refunds and abuse reports. The agent classifies "
                       "and explains, and never drafts a reply. Policy, not accuracy.",
        "all": [{"field": "status", "operator": "less_than", "value": "solved"},
                {"field": "current_tags", "operator": "includes", "value": "ai_action_hard_stop"}],
    },
    {
        "title": "2. Held for human review",
        "description": "Classified, but the claim cannot be judged from ticket text alone, "
                       "or confidence fell below the threshold.",
        "all": [{"field": "status", "operator": "less_than", "value": "solved"},
                {"field": "current_tags", "operator": "includes", "value": "ai_action_human_review"}],
    },
    {
        "title": "3. Ready to draft",
        "description": "Low-risk categories where the agent may prepare a suggested reply. "
                       "A human still reviews and sends it.",
        "all": [{"field": "status", "operator": "less_than", "value": "solved"},
                {"field": "current_tags", "operator": "includes", "value": "ai_action_auto_draft"}],
    },
    {
        "title": "4. Not yet triaged",
        "description": "Seeded tickets the agent has not processed. Should be empty.",
        "all": [{"field": "status", "operator": "less_than", "value": "solved"},
                {"field": "current_tags", "operator": "includes", "value": "seed"}],
        "any": [],
        "not": [{"field": "current_tags", "operator": "includes", "value": "ai_triaged"}],
    },
]

COLUMNS = ["subject", "requester", "created_at", "status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    zd = Zendesk()
    existing = {v["title"] for v in zd._request("GET", "/views.json").get("views", [])}

    for spec in VIEWS:
        if spec["title"] in existing:
            print(f"exists, skipping: {spec['title']}")
            continue

        payload = {
            "view": {
                "title": spec["title"],
                "description": spec["description"],
                "active": True,
                "conditions": {
                    "all": spec["all"],
                    "any": spec.get("any", []),
                },
                "execution": {
                    "columns": COLUMNS,
                    "group_by": "status",
                    "sort_by": "created_at",
                    "sort_order": "asc",
                },
            }
        }
        # The Views API takes negative conditions as "not" only on some plans; where
        # it is unavailable the view simply shows everything seeded, which still
        # reads correctly once the queue is fully triaged.
        if spec.get("not"):
            payload["view"]["conditions"]["all"] = spec["all"] + [
                dict(c, operator="not_includes") for c in spec["not"]
            ]

        if args.dry_run:
            print(f"would create: {spec['title']}")
            continue

        created = zd._request("POST", "/views.json", payload)
        print(f"created: {created['view']['title']} (id {created['view']['id']})")

    if args.dry_run:
        print("\nDry run. Nothing created.")
    else:
        print("\nOpen the agent view. The four saved views appear in the left sidebar "
              "and are what you screenshot.")


if __name__ == "__main__":
    main()
