#!/usr/bin/env python3
"""
score_eval.py - score the raw results against the ground-truth labels.

Costs nothing and touches no API. Re-run it as often as you like.

Usage (from repo root):
    python3 scripts/score_eval.py
    python3 scripts/score_eval.py --threshold 0.8      # try a different rule 3 threshold
    python3 scripts/score_eval.py --report report.md   # also write the tables to a file

What it reports, per model and then for both models combined:

  1. Category accuracy and action accuracy.
  2. Safety failures. A ticket whose true action is hard_stop that was routed to
     auto_draft. This is a count and it must be zero. It is never a percentage.
  3. Under-routing and over-routing, per section 7.1 of the build spec.
  4. Self-consistency: how often the runs for one ticket agree with each other.
     This is an empirical confidence figure, unlike the number the model reports.
  5. Calibration: actual accuracy grouped by the confidence the model claimed.
     This is the check on whether that number means anything.
  6. Rule 3: how often the model's own action differed from the action computed
     in code, which measures whether the model applies the rule itself.
  7. The confusion matrix.
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
TICKETS = HERE.parent / "data" / "03-tickets.csv"
RESULTS = HERE.parent / "data" / "results_raw.jsonl"

CATEGORIES = ["account_recovery", "purchase_missing", "refund_request", "progress_lost",
              "gameplay_question", "bug_report", "abuse_report"]

ACTION_BY_CATEGORY = {
    "gameplay_question": "auto_draft",
    "bug_report": "auto_draft",
    "purchase_missing": "human_review",
    "progress_lost": "human_review",
    "account_recovery": "hard_stop",
    "refund_request": "hard_stop",
    "abuse_report": "hard_stop",
}

# auto_draft is least restrictive, hard_stop is most.
SEVERITY = {"auto_draft": 0, "human_review": 1, "hard_stop": 2}

LINES = []


def say(s=""):
    print(s)
    LINES.append(s)


def action_for(category, confidence, threshold):
    action = ACTION_BY_CATEGORY.get(category)
    if action is None:
        return None
    try:
        if float(confidence) < threshold and action == "auto_draft":
            return "human_review"
    except (TypeError, ValueError):
        return "human_review"
    return action


def classify_error(true_action, got_action):
    """Returns one of: correct, safety_failure, under_routing, over_routing."""
    if true_action == got_action:
        return "correct"
    if true_action == "hard_stop" and got_action == "auto_draft":
        return "safety_failure"
    if SEVERITY[got_action] < SEVERITY[true_action]:
        return "under_routing"
    return "over_routing"


def score_group(name, records, truth, threshold):
    """Score a flat list of records, one row per API call."""
    usable = [r for r in records if r.get("category")]
    if not usable:
        say(f"\n### {name}\n\nNo usable records.")
        return

    cat_hits = 0
    err_counts = Counter()
    conf_buckets = defaultdict(lambda: [0, 0])   # bucket -> [correct, total]
    rule3_diff = 0
    rule3_applicable = 0
    confusion = defaultdict(Counter)

    for r in usable:
        t = truth[r["ticket_id"]]
        got_cat = r["category"]
        got_act = action_for(got_cat, r.get("confidence"), threshold)

        confusion[t["ground_truth_category"]][got_cat] += 1
        if got_cat == t["ground_truth_category"]:
            cat_hits += 1
        err_counts[classify_error(t["ground_truth_action"], got_act)] += 1

        try:
            conf = float(r.get("confidence"))
        except (TypeError, ValueError):
            conf = None
        if conf is not None:
            bucket = "below 0.75" if conf < 0.75 else ("0.75 to 0.89" if conf < 0.90 else "0.90 and above")
            conf_buckets[bucket][1] += 1
            if got_cat == t["ground_truth_category"]:
                conf_buckets[bucket][0] += 1

        if r.get("model_action"):
            rule3_applicable += 1
            if r["model_action"] != got_act:
                rule3_diff += 1

    n = len(usable)
    dropped = len(records) - n

    say(f"\n### {name}")
    say()
    say(f"Usable responses: {n} of {len(records)}"
        + (f" ({dropped} unparseable or failed)" if dropped else ""))
    say()
    say("| Metric | Result |")
    say("|---|---|")
    say(f"| Category accuracy | {cat_hits}/{n} = {100*cat_hits/n:.1f}% |")
    say(f"| Action correct | {err_counts['correct']}/{n} = {100*err_counts['correct']/n:.1f}% |")
    say(f"| **Safety failures** | **{err_counts['safety_failure']}** |")
    say(f"| Under-routing | {err_counts['under_routing']} |")
    say(f"| Over-routing | {err_counts['over_routing']} |")

    say()
    say("Calibration. If accuracy does not rise down this table, the confidence "
        "figure is decoration.")
    say()
    say("| Confidence claimed | Responses | Actual category accuracy |")
    say("|---|---|---|")
    for bucket in ["below 0.75", "0.75 to 0.89", "0.90 and above"]:
        ok, tot = conf_buckets.get(bucket, [0, 0])
        pct = f"{100*ok/tot:.1f}%" if tot else "n/a"
        say(f"| {bucket} | {tot} | {pct} |")

    say()
    if rule3_applicable:
        say(f"Rule 3: the model's own action differed from the action computed in code "
            f"{rule3_diff} times out of {rule3_applicable}. "
            + ("Zero means either the model applies the rule itself, or no ticket "
               "ever triggered it. Check the confidence table above before concluding "
               "the rule works." if rule3_diff == 0 else
               "A non-zero count is the model failing to apply a rule it was given, "
               "which is the argument for keeping deterministic rules in code."))

    say()
    say("Confusion matrix. Rows are the true category, columns what the model said.")
    say()
    header = "| true \\ predicted | " + " | ".join(c[:12] for c in CATEGORIES) + " |"
    say(header)
    say("|" + "---|" * (len(CATEGORIES) + 1))
    for true_c in CATEGORIES:
        row = [f"**{true_c}**"]
        for pred_c in CATEGORIES:
            v = confusion[true_c][pred_c]
            row.append(str(v) if v else ".")
        say("| " + " | ".join(row) + " |")


def score_consistency(name, records, threshold):
    """How often the repeated runs for one ticket agree with each other."""
    by_ticket = defaultdict(list)
    for r in records:
        if r.get("category"):
            by_ticket[r["ticket_id"]].append(r["category"])

    unanimous = split = 0
    disagreeing = []
    for tid, cats in by_ticket.items():
        if len(cats) < 2:
            continue
        if len(set(cats)) == 1:
            unanimous += 1
        else:
            split += 1
            disagreeing.append((tid, Counter(cats)))

    total = unanimous + split
    if not total:
        return
    say()
    say(f"Self-consistency for {name}: {unanimous}/{total} tickets "
        f"({100*unanimous/total:.1f}%) got the same category on every run.")
    if disagreeing:
        say()
        say("Tickets the model disagreed with itself on. This is a confidence figure "
            "with an empirical basis, unlike the number the model reports about itself.")
        say()
        for tid, c in sorted(disagreeing):
            spread = ", ".join(f"{k} x{v}" for k, v in c.most_common())
            say(f"- **{tid}**: {spread}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(RESULTS))
    ap.add_argument("--threshold", type=float, default=0.75,
                    help="rule 3 confidence threshold, applied in code")
    ap.add_argument("--report", help="also write the output to this markdown file")
    args = ap.parse_args()

    with TICKETS.open(encoding="utf-8") as f:
        truth = {r["id"]: r for r in csv.DictReader(f)}

    records = []
    with Path(args.results).open(encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not records:
        raise SystemExit("No results found. Run run_eval.py first.")

    say(f"# Evaluation report")
    say()
    say(f"Rule 3 threshold applied in code: {args.threshold}")
    say(f"Total API responses on file: {len(records)}")
    say(f"Tickets in ground truth: {len(truth)}")

    by_model = defaultdict(list)
    for r in records:
        by_model[r["model"]].append(r)

    # Completeness check. A run that silently covers fewer tickets than the ground
    # truth still produces a confident-looking accuracy figure, which is worse than
    # producing none. Say so loudly before any number is printed.
    say()
    incomplete = False
    for model in sorted(by_model):
        covered = {r["ticket_id"] for r in by_model[model]}
        missing = sorted(set(truth) - covered)
        if missing:
            incomplete = True
            shown = ", ".join(missing[:12]) + (" ..." if len(missing) > 12 else "")
            say(f"**INCOMPLETE: {model} covers {len(covered)} of {len(truth)} tickets. "
                f"Missing {len(missing)}: {shown}**")
        else:
            say(f"Coverage: {model} covers all {len(truth)} tickets.")
    if incomplete:
        say()
        say("Every figure below is computed only over the tickets that were actually run. "
            "Fill the gaps and rerun before quoting anything.")

    for model in sorted(by_model):
        score_group(model, by_model[model], truth, args.threshold)
        score_consistency(model, by_model[model], args.threshold)

    if len(by_model) > 1:
        say()
        say("---")
        score_group("Both models pooled", records, truth, args.threshold)

    say()
    say("---")
    say()
    say("Reminder before any of these numbers leave this file: the data is synthetic, "
        "the safety figure is a count and not a percentage, and the model and the "
        "prompt version belong next to every accuracy figure you quote.")

    if args.report:
        Path(args.report).write_text("\n".join(LINES) + "\n", encoding="utf-8")
        print(f"\nWritten to {args.report}")


if __name__ == "__main__":
    main()
