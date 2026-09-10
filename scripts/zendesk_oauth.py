#!/usr/bin/env python3
"""
zendesk_oauth.py - get a Zendesk OAuth access token, once.

Zendesk is retiring API tokens (they stop working 30 April 2027) and pointing
everyone at OAuth. Creating a token through the API needs a token you do not
have yet, so the first one has to come through the browser. This runs that
flow: it starts a local server, opens the consent page, catches the redirect,
exchanges the code, and writes the token into .env.

Run it once. Everything afterwards uses the token from .env.

Before running, create an OAuth client in Zendesk:
    Admin Center > Apps and integrations > APIs > OAuth Clients > add
    Client kind:   Confidential
    Redirect URL:  http://localhost:8080/callback
    Copy the secret, it is shown once.

Then put these in .env:
    ZENDESK_SUBDOMAIN=your-subdomain
    ZENDESK_OAUTH_CLIENT_ID=triage_agent_local
    ZENDESK_OAUTH_SECRET=...

Usage (from repo root):
    python3 scripts/zendesk_oauth.py
"""

import http.server
import os
import re
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zendesk_client import load_env_file

HERE = Path(__file__).parent
ENV_FILE = HERE.parent / ".env"
PORT = 8080
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPES = "read write"

_result = {}


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        _result["code"] = (params.get("code") or [None])[0]
        _result["state"] = (params.get("state") or [None])[0]
        _result["error"] = (params.get("error_description") or params.get("error") or [None])[0]

        ok = bool(_result["code"])
        body = (
            "<html><body style='font-family:system-ui;padding:3rem;max-width:32rem'>"
            + ("<h2>Authorised.</h2><p>You can close this tab and go back to the terminal.</p>"
               if ok else
               f"<h2>Something went wrong.</h2><pre>{_result['error']}</pre>")
            + "</body></html>"
        )
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        pass          # keep the terminal clean


def write_env(key, value):
    """Set key=value in .env, replacing an existing line rather than duplicating it."""
    text = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    line = f"{key}={value}"
    if re.search(rf"^{re.escape(key)}=.*$", text, re.M):
        text = re.sub(rf"^{re.escape(key)}=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    ENV_FILE.write_text(text, encoding="utf-8")


def main():
    load_env_file()
    sub = os.environ.get("ZENDESK_SUBDOMAIN")
    client_id = os.environ.get("ZENDESK_OAUTH_CLIENT_ID")
    secret = os.environ.get("ZENDESK_OAUTH_SECRET")
    missing = [n for n, v in [("ZENDESK_SUBDOMAIN", sub),
                              ("ZENDESK_OAUTH_CLIENT_ID", client_id),
                              ("ZENDESK_OAUTH_SECRET", secret)] if not v]
    if missing:
        sys.exit("Missing from .env: " + ", ".join(missing) + "\n" + __doc__)

    state = secrets.token_urlsafe(16)
    auth_url = (
        f"https://{sub}.zendesk.com/oauth/authorizations/new?"
        + urllib.parse.urlencode({
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "scope": SCOPES,
            "state": state,
        })
    )

    server = http.server.HTTPServer(("localhost", PORT), CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print(f"Listening on {REDIRECT_URI}")
    print("Opening the consent page. If nothing opens, paste this into a browser:\n")
    print(auth_url + "\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print("Waiting for you to approve...")
    while "code" not in _result and "error" not in _result:
        pass
    server.shutdown()

    if not _result.get("code"):
        sys.exit(f"Authorisation failed: {_result.get('error')}")
    if _result.get("state") != state:
        sys.exit("State mismatch. Aborting rather than trusting this redirect.")

    print("Code received. Exchanging it for a token...")
    r = requests.post(
        f"https://{sub}.zendesk.com/oauth/tokens",
        json={
            "grant_type": "authorization_code",
            "code": _result["code"],
            "client_id": client_id,
            "client_secret": secret,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        },
        timeout=60,
    )
    if r.status_code >= 300:
        sys.exit(f"Token exchange failed: {r.status_code} {r.text[:400]}")

    token = r.json()["access_token"]
    write_env("ZENDESK_OAUTH_TOKEN", token)
    print(f"\nToken written to .env as ZENDESK_OAUTH_TOKEN ({token[:8]}...).")
    print("Next: python3 seed_tickets.py --check")


if __name__ == "__main__":
    main()
