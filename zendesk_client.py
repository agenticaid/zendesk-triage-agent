#!/usr/bin/env python3
"""
zendesk_client.py - the small amount of Zendesk API surface this project needs.

Five calls, one retry policy, one credential loader. Imported by seed_tickets.py
and backfill_zendesk.py so neither of them repeats this.

Auth is HTTP Basic with the username "<email>/token" and the API token as the
password. Zendesk is deprecating API tokens in favour of OAuth by April 2027;
for a 14-day demo the token is the right call.
"""

import json
import os
import random
import sys
import time
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

HERE = Path(__file__).parent


def load_env_file(path: Path = None):
    """Read a .env file next to this script into os.environ. Shell wins over file."""
    path = path or (HERE / ".env")
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class Zendesk:
    """Two auth paths, OAuth preferred.

    Zendesk stops accepting API tokens on 30 April 2027 and directs everyone to
    OAuth, so an OAuth bearer token is used when one is present and the API
    token is only a fallback. Run zendesk_oauth.py once to obtain the bearer
    token; it lands in .env as ZENDESK_OAUTH_TOKEN.
    """

    def __init__(self):
        load_env_file()
        sub = os.environ.get("ZENDESK_SUBDOMAIN")
        if not sub:
            sys.exit("Missing from .env: ZENDESK_SUBDOMAIN")
        self.base = f"https://{sub}.zendesk.com/api/v2"

        oauth = os.environ.get("ZENDESK_OAUTH_TOKEN")
        if oauth:
            self.auth = None
            self.headers = {"Authorization": f"Bearer {oauth}"}
            self.auth_kind = "oauth"
            return

        email = os.environ.get("ZENDESK_EMAIL")
        token = os.environ.get("ZENDESK_API_TOKEN")
        if not (email and token):
            sys.exit(
                "No credentials. Either run:\n"
                "    python3 zendesk_oauth.py      (preferred, OAuth)\n"
                "or set ZENDESK_EMAIL and ZENDESK_API_TOKEN in .env."
            )
        self.auth = HTTPBasicAuth(f"{email}/token", token)
        self.headers = {}
        self.auth_kind = "api_token"

    def _request(self, method, path, payload=None, params=None, attempts=5):
        """One call, with backoff on rate limits and transient server errors.

        Zendesk enforces a per-minute rate limit and answers 429 with a
        Retry-After header. Respecting it is cheaper than discovering it at
        ticket 60 of 90.
        """
        url = path if path.startswith("http") else f"{self.base}{path}"
        for attempt in range(attempts):
            try:
                r = requests.request(method, url, auth=self.auth, headers=self.headers,
                                     json=payload, params=params, timeout=60)
            except requests.RequestException as exc:
                if attempt == attempts - 1:
                    raise
                time.sleep(2 ** attempt + random.random())
                continue

            if r.status_code < 300:
                return r.json() if r.text else {}

            if r.status_code == 429 or r.status_code >= 500:
                if attempt == attempts - 1:
                    raise RuntimeError(f"{method} {url} -> {r.status_code} after {attempts} tries")
                wait = float(r.headers.get("Retry-After", 0)) or (2 ** attempt + random.random())
                print(f"    {r.status_code}, waiting {wait:.0f}s")
                time.sleep(wait)
                continue

            raise RuntimeError(f"{method} {url} -> {r.status_code}: {r.text[:300]}")

        raise RuntimeError("attempts exhausted")

    # --- the five calls this project uses ---

    def whoami(self):
        return self._request("GET", "/users/me.json")["user"]

    def create_many(self, tickets):
        """Async bulk create. Returns a job status url to poll."""
        return self._request("POST", "/tickets/create_many.json", {"tickets": tickets})

    def job_status(self, job_url):
        return self._request("GET", job_url)

    def list_tickets(self):
        """All tickets, following cursor pagination."""
        out, params = [], {"page[size]": 100}
        path = "/tickets.json"
        while True:
            data = self._request("GET", path, params=params)
            out.extend(data.get("tickets", []))
            meta = data.get("meta") or {}
            if not meta.get("has_more"):
                return out
            params = {"page[size]": 100, "page[after]": meta["after_cursor"]}

    def get_ticket(self, ticket_id):
        return self._request("GET", f"/tickets/{ticket_id}.json")["ticket"]

    def update_ticket(self, ticket_id, tags=None, internal_note=None):
        """Set tags and add a private comment.

        Note that sending `tags` REPLACES the whole tag list rather than adding
        to it, which is why the callers always send the complete intended set.
        `public: false` is what makes the comment an internal note; get it wrong
        and you have emailed a fictional player your debugging output.
        """
        ticket = {}
        if tags is not None:
            ticket["tags"] = tags
        if internal_note:
            ticket["comment"] = {"body": internal_note, "public": False}
        return self._request("PUT", f"/tickets/{ticket_id}.json", {"ticket": ticket})
