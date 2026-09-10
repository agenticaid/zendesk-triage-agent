#!/usr/bin/env python3
"""
run_eval.py - classify every ticket N times on each model and record the raw results.

This is the script that costs money. It does nothing but call the API and append
results to a JSONL file. All scoring happens in score_eval.py, which is free and
can be re-run as many times as you like against the same raw data.

Every API call is independent. There is no conversation, no session and no memory
between calls, so there is nothing to "clear" between tickets.

Usage (from repo root):
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 scripts/run_eval.py --sample          # the 10 round-1 tickets, 60 calls
    python3 scripts/run_eval.py                   # all 90 tickets, 540 calls
    python3 scripts/run_eval.py --models claude-sonnet-5 --runs 1    # cheap smoke test

Safe to interrupt and rerun. Completed calls are skipped on the next run.
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).parent
TICKETS = HERE.parent / "data" / "03-tickets.csv"
PROMPT = HERE.parent / "prompts" / "prompt_classify_v1.txt"
RESULTS = HERE.parent / "data" / "results_raw.jsonl"

MODELS = ["claude-sonnet-5", "claude-opus-5"]
RUNS_PER_MODEL = 3

# Temperature must be above zero. The point of running each ticket several times
# is to see how much the answer moves, and at temperature 0 it would not move at all,
# which would tell us nothing about the model's stability.
TEMPERATURE = 1.0

MAX_TOKENS = 1500  # must cover thinking tokens plus the JSON; 300 truncated mid-answer
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# The 10 tickets used for the round 1 hand test.
SAMPLE_IDS = ["T007", "T009", "T033", "T035", "T046",
              "T023", "T021", "T057", "T072", "T084"]

VALID_CATEGORIES = {
    "account_recovery", "purchase_missing", "refund_request", "progress_lost",
    "gameplay_question", "bug_report", "abuse_report",
}

# The category to action mapping, held in code rather than trusted to the model.
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


def load_env_file(path: Path = None):
    """Read a .env file sitting next to this script into os.environ.

    Hand-rolled rather than pulling in python-dotenv, because it is fifteen lines
    and one less thing to install. Existing environment variables win, so an
    explicit `export` in the shell always overrides the file.
    """
    path = path or (HERE.parent / ".env")
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def computed_action(category: str, confidence) -> str:
    """Rule 3 applied in code: the mapping, then a downgrade on low confidence.

    Recorded alongside the action the model reported. The two disagreeing is the
    measurement of whether the model applies rule 3 itself.
    """
    action = ACTION_BY_CATEGORY.get(category)
    if action is None:
        return "invalid"
    try:
        if float(confidence) < CONFIDENCE_THRESHOLD and action == "auto_draft":
            return "human_review"
    except (TypeError, ValueError):
        return "human_review"
    return action


def extract_json(text: str):
    """Pull the JSON object out of a model response.

    Handles a bare object, a fenced code block, and an object with prose around it.
    Returns None if nothing parses, which is itself a result worth recording.
    """
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def call_model(api_key: str, model: str, prompt: str, attempt_budget: int = 5):
    """One API call, with backoff on rate limits and transient server errors."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "messages": [{"role": "user", "content": prompt}],
    }

    for attempt in range(attempt_budget):
        try:
            r = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        except requests.RequestException as exc:
            if attempt == attempt_budget - 1:
                return None, None, f"network: {exc}"
            time.sleep(2 ** attempt + random.random())
            continue

        if r.status_code == 200:
            body = r.json()
            text = "".join(b.get("text", "") for b in body.get("content", []))
            return text, body.get("usage", {}), None

        if r.status_code in (429, 500, 502, 503, 529):
            if attempt == attempt_budget - 1:
                return None, None, f"http {r.status_code} after {attempt_budget} attempts"
            wait = float(r.headers.get("retry-after", 0)) or (2 ** attempt + random.random())
            time.sleep(wait)
            continue

        return None, None, f"http {r.status_code}: {r.text[:200]}"

    return None, None, "exhausted attempts"


def load_done(path: Path):
    """(ticket, model, run) triples already recorded, so a rerun resumes."""
    done = set()
    if not path.exists():
        return done
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("error") is None:
                done.add((rec["ticket_id"], rec["model"], rec["run"]))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true",
                    help="only the 10 tickets from the round 1 hand test")
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--runs", type=int, default=RUNS_PER_MODEL)
    ap.add_argument("--out", default=str(RESULTS))
    args = ap.parse_args()

    load_env_file()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "ANTHROPIC_API_KEY not found.\n"
            "Either create a .env file next to this script containing:\n"
            "    ANTHROPIC_API_KEY=sk-ant-...\n"
            "or export it in the shell before running."
        )

    template = PROMPT.read_text(encoding="utf-8")
    with TICKETS.open(encoding="utf-8") as f:
        tickets = list(csv.DictReader(f))
    if args.sample:
        tickets = [t for t in tickets if t["id"] in SAMPLE_IDS]

    out = Path(args.out)
    done = load_done(out)

    planned = len(tickets) * len(args.models) * args.runs
    todo = planned - len(done)
    print(f"{len(tickets)} tickets x {len(args.models)} models x {args.runs} runs "
          f"= {planned} calls, {len(done)} already done, {todo} to make.")
    if todo == 0:
        print("Nothing to do. Run score_eval.py.")
        return

    in_tok = out_tok = 0
    failures = 0
    started = time.time()

    with out.open("a", encoding="utf-8") as sink:
        for model in args.models:
            for run in range(1, args.runs + 1):
                for t in tickets:
                    key = (t["id"], model, run)
                    if key in done:
                        continue

                    prompt = (template
                              .replace("{{subject}}", t["subject"])
                              .replace("{{body}}", t["body"]))
                    text, usage, error = call_model(api_key, model, prompt)

                    parsed = extract_json(text) if text else None
                    category = (parsed or {}).get("category")
                    if category not in VALID_CATEGORIES:
                        category = None

                    rec = {
                        "ticket_id": t["id"],
                        "model": model,
                        "run": run,
                        "category": category,
                        "model_action": (parsed or {}).get("action"),
                        "confidence": (parsed or {}).get("confidence"),
                        "secondary_category": (parsed or {}).get("secondary_category"),
                        "reason": (parsed or {}).get("reason"),
                        "computed_action": computed_action(
                            category, (parsed or {}).get("confidence")) if category else None,
                        "raw": text,
                        "error": error or (None if parsed else "unparseable response"),
                        "usage": usage,
                    }
                    sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    sink.flush()

                    if usage:
                        in_tok += usage.get("input_tokens", 0)
                        out_tok += usage.get("output_tokens", 0)
                    if rec["error"]:
                        failures += 1
                        print(f"  ! {t['id']} {model} run{run}: {rec['error']}")
                    else:
                        print(f"  . {t['id']} {model} run{run} -> "
                              f"{category} / {rec['computed_action']} "
                              f"(conf {rec['confidence']})")

    mins = (time.time() - started) / 60
    print(f"\nDone in {mins:.1f} min. {failures} failed calls.")
    print(f"Tokens: {in_tok:,} in, {out_tok:,} out.")
    print("Multiply by the current per-token price for each model to get the cost. "
          "Check the pricing page rather than trusting a number written months ago.")
    print(f"Raw results appended to {out}. Now run: python3 score_eval.py")


if __name__ == "__main__":
    main()
