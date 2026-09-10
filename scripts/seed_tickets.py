#!/usr/bin/env python3
"""
seed_tickets.py - load the 90 synthetic tickets into the Zendesk trial.

Each ticket carries its CSV id in Zendesk's `external_id` field, which is what
that field is for: the id of this record in your own system. Everything
afterwards maps back through it, so nothing depends on creation order or on
the ids Zendesk happens to assign.

Usage (from repo root):
    python3 scripts/seed_tickets.py --check      # verify credentials, create nothing
    python3 scripts/seed_tickets.py --dry-run    # show what would be created
    python3 scripts/seed_tickets.py              # create them

Safe to run twice: it lists what already exists and only creates the rest.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zendesk_client import Zendesk

HERE = Path(__file__).parent
TICKETS = HERE.parent / "data" / "03-tickets.csv"
MAP_FILE = HERE.parent / "data" / "zendesk_ticket_map.json"


def build_payload(row):
    return {
        "external_id": row["id"],
        "subject": row["subject"],
        "comment": {"body": row["body"], "public": True},
        "requester": {
            "name": f"Player {row['id'][1:]}",
            # example.com is reserved by RFC 2606 and cannot receive mail, and unlike
            # .invalid it survives Zendesk's email validation, which checks the TLD
            # against a real list rather than against the standard.
            "email": f"player{row['id'][1:].lower()}@example.com",
        },
        "tags": ["seed", "synthetic"],
        "status": "new",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify credentials only")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    zd = Zendesk()

    me = zd.whoami()
    print(f"Authenticated as {me['name']} <{me['email']}>, role {me['role']}")
    if args.check:
        return

    with TICKETS.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"{len(rows)} tickets in the CSV.")

    existing = {t.get("external_id"): t["id"] for t in zd.list_tickets() if t.get("external_id")}
    if existing:
        print(f"{len(existing)} already exist in Zendesk and will be skipped.")

    todo = [r for r in rows if r["id"] not in existing]
    if not todo:
        print("Nothing to create.")
    else:
        print(f"Creating {len(todo)}.")
        if args.dry_run:
            for r in todo[:5]:
                print("  would create:", r["id"], "|", r["subject"])
            print("  ...")
            return

        # create_many takes up to 100 per call, so 90 is a single batch.
        for i in range(0, len(todo), 100):
            batch = [build_payload(r) for r in todo[i:i + 100]]
            job = zd.create_many(batch)
            job_url = job["job_status"]["url"]
            print(f"  batch of {len(batch)} submitted, polling the job...")

            # create_many is asynchronous: the response is a job, not the tickets.
            for _ in range(40):
                time.sleep(3)
                status = zd.job_status(job_url)["job_status"]
                if status["status"] == "completed":
                    # "Processed" is not "succeeded". The job reports a per-item
                    # result and a batch can complete with every item failed, which
                    # is exactly what happened on the first run of this script.
                    results = status.get("results") or []
                    failures = [r for r in results if r.get("error")]
                    print(f"  job completed. {len(results)} processed, {len(failures)} failed.")
                    for r in failures[:5]:
                        print(f"    ! index {r.get('index')}: {r.get('error')} - {r.get('details')}")
                    if len(failures) > 5:
                        print(f"    ! and {len(failures) - 5} more with the same shape")
                    break
                print(f"    {status['status']} {status.get('progress')}/{status.get('total')}")
            else:
                print("  job did not report completion in time; check Zendesk before rerunning")

    # Rebuild the map from what is actually in Zendesk rather than from what we
    # believe we sent.
    time.sleep(3)
    mapping = {t["external_id"]: t["id"] for t in zd.list_tickets() if t.get("external_id")}
    MAP_FILE.write_text(json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8")

    missing = sorted({r["id"] for r in rows} - set(mapping))
    print(f"\nMapped {len(mapping)} tickets into {MAP_FILE.name}")
    if missing:
        print(f"MISSING {len(missing)}: {', '.join(missing[:15])}")
        print("Rerun this script; it will create only the missing ones.")
    else:
        print("All 90 present. Next: python3 backfill_zendesk.py --dry-run")


if __name__ == "__main__":
    main()
