#!/usr/bin/env python3
"""
main.py - the Cloud Run service a native Zendesk trigger calls on a new ticket.

One route: POST /triage {"ticket_id": <zendesk id>}. Fetches the ticket,
classifies it, drafts a reply if and only if the computed action is
auto_draft, and writes tags plus internal note(s) back to Zendesk. Nothing
here is ever posted as a public comment.

Reuses the same category/action logic, prompts, and note formatting as
scripts/backfill_zendesk.py and scripts/draft_replies.py so a live ticket is
triaged identically to the 90 seeded ones.
"""

import json
import os
from pathlib import Path

from flask import Flask, jsonify, request

from scripts.backfill_zendesk import ACTION_BY_CATEGORY, computed_action, build_note
from scripts.draft_replies import MODEL, call_model, note_for
from zendesk_client import Zendesk, load_env_file

HERE = Path(__file__).parent
CLASSIFY_PROMPT = HERE / "prompts" / "prompt_classify_v1.txt"
DRAFT_PROMPT = HERE / "prompts" / "prompt_draft_v1.txt"

load_env_file()

app = Flask(__name__)


def classify(api_key, subject, body):
    template = CLASSIFY_PROMPT.read_text(encoding="utf-8")
    prompt = template.replace("{{subject}}", subject).replace("{{body}}", body)
    raw = call_model(api_key, prompt)
    return json.loads(raw)


def draft(api_key, category, subject, body):
    template = DRAFT_PROMPT.read_text(encoding="utf-8")
    prompt = (template.replace("{{category}}", category)
                       .replace("{{subject}}", subject)
                       .replace("{{body}}", body))
    return call_model(api_key, prompt)


@app.post("/triage")
def triage():
    expected = os.environ.get("TRIAGE_WEBHOOK_SECRET")
    if expected and request.headers.get("X-Webhook-Secret") != expected:
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(force=True, silent=True) or {}
    ticket_id = payload.get("ticket_id")
    if not ticket_id:
        return jsonify({"error": "ticket_id required"}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500

    zd = Zendesk()
    ticket = zd.get_ticket(ticket_id)

    if "ai_triaged" in (ticket.get("tags") or []):
        return jsonify({"ticket_id": ticket_id, "skipped": "already triaged"}), 200

    subject = ticket.get("subject") or ""
    body = ticket.get("description") or ""

    rec = classify(api_key, subject, body)
    category = rec.get("category")
    if category not in ACTION_BY_CATEGORY:
        return jsonify({"error": f"unrecognised category: {category}"}), 502
    rec["model"] = MODEL

    action = computed_action(category, rec.get("confidence"))
    tags = ["ai_triaged", f"ai_cat_{category}", f"ai_action_{action}"]

    note = build_note(rec, action, {"id": ticket_id})
    zd.update_ticket(ticket_id, tags=tags, internal_note=note)

    result = {"ticket_id": ticket_id, "category": category, "action": action,
              "confidence": rec.get("confidence")}

    if action == "auto_draft":
        reply = draft(api_key, category, subject, body)
        draft_tags = tags + ["ai_drafted"]
        zd.update_ticket(ticket_id, tags=draft_tags, internal_note=note_for(reply, category))
        result["drafted"] = True

    return jsonify(result), 200


@app.get("/status")
def healthz():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
