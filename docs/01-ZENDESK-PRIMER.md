# Zendesk from Zero

You have never used Zendesk. This gets you to competent in about ninety minutes. Read it once through before clicking anything.

---

## 1. What Zendesk actually is

Zendesk is a queue of customer conversations plus a set of rules for moving them around. That is the whole product. Everything else is decoration on those two ideas.

If it helps: think of it as a shared inbox where every email thread is a database row with a status, an owner, and labels, and where you can write rules that fire when a row changes.

## 2. The seven objects you need to know

Learn these and you can hold a conversation about Zendesk with anyone.

**Ticket.** One customer's issue, from first message to resolution. It has a subject, a description (the first message), and then a series of **comments**. It has a status: New, Open, Pending, On-hold, Solved, Closed. It has a requester (the customer) and an assignee (the agent). This is the only object that really matters.

**Comment.** A message on a ticket. Two kinds, and the difference is important for you: a **public comment** is visible to the customer, an **internal note** is visible only to agents. Your agent will write internal notes explaining its decisions. It will never write a public comment automatically in this build.

**Tag.** A free-text label on a ticket. No structure, no validation, you invent them. This is how your agent will mark its classification: `ai_cat_purchase_missing`, `ai_action_hard_stop`, and so on. Tags are the cheapest way to get structured data onto a ticket and they are searchable.

**Custom field.** A proper typed field you define (dropdown, text, number). More structured than a tag, more setup. You do not need these. Use tags.

**View.** A saved filter over the queue. "All tickets with tag `ai_action_human_review`, sorted by oldest first." Views are what agents actually stare at all day. You will make one or two so your screenshots look like a real queue.

**Trigger.** A rule that fires immediately when a ticket is created or updated. "When a ticket is created and the subject contains 'refund', add tag `billing`." This is Zendesk's built-in automation, and it is worth understanding because part of your interview answer is knowing when a trigger is enough and an LLM is overkill.

**Automation.** Like a trigger, but time-based. Fires on a schedule against tickets matching conditions. "If a ticket has been Pending for 4 days, close it." You do not need these.

**Macro.** A canned response an agent applies with one click. Relevant to you conceptually: your agent's drafted replies are essentially dynamically generated macros, and that is a good line to have ready.

## 3. The two interfaces

Zendesk has two separate web interfaces and new users get lost between them constantly.

**The Agent Workspace** is where tickets live. It looks like an email client. This is where you go to see the queue.

**Admin Center** is where settings live, including your API token. You get to it from the gear or grid icon. It is a different app with a different navigation tree. When a guide says "go to Admin Center," it does not mean the settings menu inside the agent view.

## 4. Setup: the exact path

### 4.1 The trial

Sign up at https://www.zendesk.com/register/free-trial/

You pick a **subdomain**. Choose something you are willing to have in your README, for example `erez-triage-demo`. Your instance lives at `https://<subdomain>.zendesk.com` and your API base is `https://<subdomain>.zendesk.com/api/v2/`.

**The trial is 14 days.** Start it on Day 1 morning, not before.

### 4.2 The API token

Admin Center → **Apps and integrations** → **APIs** → **Zendesk API** → **API tokens** tab → **Add API token**.

Give it a description, save, and **copy the token immediately**. Zendesk never shows it again. If you lose it, delete it and make a new one.

You may need to switch API token access on in that same screen first.

Source for the path and the one-time-display behaviour: [Zendesk help](https://support.zendesk.com/hc/en-us/articles/4408889192858-Managing-API-token-access-to-the-Zendesk-API).

One footnote worth knowing, and worth mentioning in an interview because it shows you read the docs rather than a blog post: Zendesk is deprecating API tokens, with an end date of 30 April 2027, in favour of OAuth. For a 14-day demo the token is the right call. Knowing it is deprecated is the part that signals care. Same source.

### 4.3 How authentication works

HTTP Basic auth, where the username is your email with `/token` appended and the password is the token.

```
username: erezcohen85@gmail.com/token
password: <your api token>
```

In Python with `requests`:

```python
import requests
from requests.auth import HTTPBasicAuth

SUBDOMAIN = "erez-triage-demo"
EMAIL = "erezcohen85@gmail.com"
TOKEN = "..."          # keep this in an env var, never in the repo

auth = HTTPBasicAuth(f"{EMAIL}/token", TOKEN)
base = f"https://{SUBDOMAIN}.zendesk.com/api/v2"

r = requests.get(f"{base}/tickets.json", auth=auth)
print(r.status_code, r.json())
```

Put the token in a `.env` file and add `.env` to `.gitignore` before your first commit. A leaked credential in a portfolio repo is the one mistake that turns this asset into a liability.

## 5. The five API calls you will use

You do not need to learn the Zendesk API. You need these five.

**Create a ticket.** `POST /api/v2/tickets.json`

```json
{
  "ticket": {
    "subject": "I paid and got nothing",
    "comment": { "body": "bought the 10 dollar pack, coins never came" },
    "requester": { "name": "Player 41", "email": "player41@example.com" },
    "tags": ["seed"]
  }
}
```

**Create many tickets at once.** `POST /api/v2/tickets/create_many.json` with `{"tickets": [ ... ]}`. Up to 100 per call. This is how you seed the CSV in one or two calls instead of ninety. It returns a job id; the tickets appear a moment later.

**Read one ticket.** `GET /api/v2/tickets/{id}.json`

**Update a ticket: add tags and an internal note.** `PUT /api/v2/tickets/{id}.json`

```json
{
  "ticket": {
    "tags": ["ai_cat_purchase_missing", "ai_action_human_review"],
    "comment": {
      "body": "Triage agent: purchase_missing, confidence 0.86. Held for human review because the claim needs receipt verification.",
      "public": false
    }
  }
}
```

`"public": false` is what makes it an internal note. Get this wrong and you have emailed a fictional player your debugging output.

Note that sending `tags` on an update **replaces** the whole tag list. If you want to add without clobbering, either read the existing tags first and send the union, or use `PUT /api/v2/tickets/{id}/tags.json` which appends.

**Search.** `GET /api/v2/search.json?query=type:ticket tags:seed -tags:ai_triaged`

This is your fallback trigger: poll for tickets that are seeded but not yet triaged.

Reference: [Creating and updating tickets](https://developer.zendesk.com/documentation/ticketing/managing-tickets/creating-and-updating-tickets/).

## 6. Rate limits and other things that will bite you

- There is a per-minute API rate limit that varies by plan. If you get a `429`, read the `Retry-After` header and sleep. Write that handling into the seeding script from the start rather than after it fails at ticket 60.
- `create_many` is asynchronous. The response is a job status, not the tickets. Poll the job or just wait ten seconds.
- Tickets created by the API with a new requester email will create that user. Ninety fake players is fine on a trial.
- Solved tickets close permanently after a few days and become read-only. Leave everything Open or New.

## 7. Vocabulary for the interview

If you can use these words correctly in a sentence you will sound like someone who has worked in support tooling.

- **Deflection** — a contact resolved without a human agent touching it. Never use it about this build.
- **First response time** and **full resolution time** — the two SLA clocks everyone tracks.
- **Backlog** — open tickets not yet resolved.
- **Escalation path** — where a ticket goes when tier one cannot solve it.
- **Macro** — canned response.
- **Side conversation** — a thread with someone outside the ticket, for example another internal team.
- **Light agent** — a user who can read tickets and write internal notes but not reply to customers. Conceptually this is exactly the permission level your agent should have, and saying so is a good answer to "how would you deploy this safely."
