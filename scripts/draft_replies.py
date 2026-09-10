#!/usr/bin/env python3
"""
draft_replies.py - generate suggested replies for the auto_draft tickets only.

This is the first and only place in the project where a model writes text that
is aimed at a customer, so it is also the only place where the output has to be
read rather than measured. Every draft lands as an internal note. Nothing is
ever posted publicly, and no code path here can post publicly.

The gate is deliberately narrow: a ticket is drafted only if its computed action
is auto_draft, which means the classifier chose gameplay_question or bug_report
AND confidence cleared the threshold. Everything else is skipped without asking
the model anything.

Usage (from repo root):
    python3 scripts/draft_replies.py --dry-run      # generate, save locally, post nothing
    python3 scripts/draft_replies.py                # generate and post as internal notes
    python3 scripts/draft_replies.py --review       # print the saved drafts and stop

Drafts are cached in data/drafts.jsonl so review and reposting cost nothing.
"""

import argparse
import csv
import json
import os
import random
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zendesk_client import Zendesk, load_env_file

HERE = Path(__file__).parent
RESULTS = HERE.parent / "data" / "results_raw.jsonl"
TICKETS = HERE.parent / "data" / "03-tickets.csv"
MAP_FILE = HERE.parent / "data" / "zendesk_ticket_map.json"
PROMPT = HERE.parent / "prompts" / "prompt_draft_v1.txt"
DRAFTS = HERE.parent / "data" / "drafts.jsonl"

MODEL = "claude-sonnet-5"
MAX_TOKENS = 1500
TEMPERATURE = 1.0
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

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


def call_model(api_key, prompt, attempts=5):
    headers = {"x-api-key": api_key, "anthropic-version": API_VERSION,
               "content-type": "application/json"}
    payload = {"model": MODEL, "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE,
               "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(attempts):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt + random.random())
            continue
        if r.status_code == 200:
            body = r.json()
            return "".join(b.get("text", "") for b in body.get("content", [])).strip()
        if r.status_code in (429, 500, 502, 503, 529):
            if attempt == attempts - 1:
                raise RuntimeError(f"{r.status_code} after {attempts} tries")
            time.sleep(float(r.headers.get("retry-after", 0)) or (2 ** attempt + random.random()))
            continue
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    raise RuntimeError("attempts exhausted")


def note_for(draft, category):
    # Everything after the blank line is the draft, verbatim, with nothing after it.
    # An agent selects from the blank line to the end of the note and pastes straight
    # into the public reply. Category, confidence and model already live on the
    # separate TRIAGE AGENT note this ticket got from backfill_zendesk.py; repeating
    # them here would just be more text between the agent and the thing they need to copy.
    return "\n".join([
        "SUGGESTED REPLY, NOT SENT. Copy everything below this line into the public "
        "reply, edit as needed, then send.",
        "",
        draft,
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="generate and cache, post nothing")
    ap.add_argument("--review", action="store_true", help="print cached drafts and exit")
    ap.add_argument("--force", action="store_true", help="regenerate even if cached")
    args = ap.parse_args()

    with TICKETS.open(encoding="utf-8") as f:
        truth = {r["id"]: r for r in csv.DictReader(f)}

    cached = {}
    if DRAFTS.exists():
        for line in DRAFTS.open(encoding="utf-8"):
            try:
                d = json.loads(line)
                cached[d["ticket_id"]] = d
            except json.JSONDecodeError:
                pass

    if args.review:
        if not cached:
            sys.exit("No cached drafts. Run with --dry-run first.")
        for tid in sorted(cached):
            d = cached[tid]
            print(f"\n{'=' * 70}\n{tid}  [{d['category']}]  {truth[tid]['subject']}")
            print(f"  player: {truth[tid]['body']}")
            print(f"{'-' * 70}\n{d['draft']}")
        print(f"\n{len(cached)} drafts. Read every one before posting.")
        return

    # Pick the auto_draft tickets from the stored classifications.
    picked = {}
    with RESULTS.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("model") == MODEL and r.get("category") and not r.get("error"):
                picked.setdefault(r["ticket_id"], r)

    targets = {tid: r for tid, r in picked.items()
               if computed_action(r["category"], r.get("confidence")) == "auto_draft"}
    print(f"{len(targets)} tickets in auto_draft. Everything else is skipped without "
          f"asking the model anything.")

    todo = sorted(t for t in targets if args.force or t not in cached)
    if todo:
        load_env_file()
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            sys.exit("ANTHROPIC_API_KEY not found in .env")
        template = PROMPT.read_text(encoding="utf-8")

        with DRAFTS.open("a", encoding="utf-8") as sink:
            for n, tid in enumerate(todo, 1):
                row, rec = truth[tid], targets[tid]
                prompt = (template
                          .replace("{{category}}", rec["category"])
                          .replace("{{subject}}", row["subject"])
                          .replace("{{body}}", row["body"]))
                draft = call_model(api_key, prompt)
                entry = {"ticket_id": tid, "category": rec["category"],
                         "model": MODEL, "draft": draft}
                sink.write(json.dumps(entry, ensure_ascii=False) + "\n")
                sink.flush()
                cached[tid] = entry
                print(f"  {n}/{len(todo)} {tid} [{rec['category']}] {len(draft.split())} words")
    else:
        print("All drafts already cached.")

    if args.dry_run:
        print(f"\nCached in {DRAFTS.name}. Nothing posted.")
        print("Read them all: python3 draft_replies.py --review")
        return

    if not MAP_FILE.exists():
        sys.exit("data/zendesk_ticket_map.json not found.")
    mapping = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    zd = Zendesk()

    already = {t["external_id"] for t in zd.list_tickets()
               if t.get("external_id") and "ai_drafted" in (t.get("tags") or [])}
    to_post = [t for t in sorted(targets) if t not in already]
    if already:
        print(f"\n{len(already)} already have a draft posted, skipping.")

    for n, tid in enumerate(to_post, 1):
        rec = targets[tid]
        tags = ["seed", "synthetic", "ai_triaged", "ai_drafted",
                f"ai_cat_{rec['category']}", "ai_action_auto_draft"]
        zd.update_ticket(mapping[tid], tags=tags,
                         internal_note=note_for(cached[tid]["draft"], rec["category"]))
        print(f"  {n}/{len(to_post)} {tid} -> #{mapping[tid]}")

    print(f"\n{len(to_post)} drafts posted as internal notes. "
          "None of them is visible to a player.")


if __name__ == "__main__":
    main()
