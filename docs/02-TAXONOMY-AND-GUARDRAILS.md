# Taxonomy and Guardrails

This is the document that gets you the interview. The code is replaceable. This is the thinking.

The premise: an automation that can reply to a customer can also be manipulated into replying to the wrong customer. In a mobile game, the highest-value thing an attacker wants is someone else's account, and the front door to someone else's account is the support queue. So the design question is not "how much can we automate" but "what must never be automated, and why."

---

## The seven categories

| Code | Name | What it looks like |
|---|---|---|
| `account_recovery` | Account access | Lost the account after changing phone, uninstalled and lost progress, cannot log in, "this is my account, please restore it" |
| `purchase_missing` | Paid, not delivered | Charged for coins, spins or a pack that never arrived |
| `refund_request` | Wants money back | Asking to reverse a charge, disputing a purchase, a child spent money |
| `progress_lost` | Progress or items gone | Village reset, level went backwards, items disappeared after an update |
| `gameplay_question` | How does X work | Event rules, what a feature does, when something unlocks |
| `bug_report` | Something is broken | Crash, freeze, black screen, button does nothing, visual glitch |
| `abuse_report` | Another player | Cheating, harassment, scam links, impersonation |

Seven is deliberate. Fewer and the categories stop being actionable. More and the model's errors become unmeasurable on ninety tickets.

---

## The three action levels

| Action | What the agent does | What a human does |
|---|---|---|
| `auto_draft` | Writes a suggested public reply and attaches it as an internal note | Reads it, edits if needed, sends |
| `human_review` | Classifies and tags, writes an internal note explaining what it found, drafts nothing | Handles the ticket normally, with the triage as a head start |
| `hard_stop` | Classifies and tags only. Writes an internal note that says explicitly why it refused. Never drafts text. | Handles it entirely |

Note that even `auto_draft` does not send anything to a customer. A human presses send. This is a deliberate choice and you should say so: the value in the first version of a triage system is routing and preparation, not autonomy. You earn autonomy after you have accuracy data, and on day one you have none.

---

## The policy

| Category | Action | Reasoning |
|---|---|---|
| `gameplay_question` | `auto_draft` | Factual, public information. Worst case of a wrong answer is a mildly annoyed player. No account state changes, no money. |
| `bug_report` | `auto_draft` | The correct first reply is nearly always the same: acknowledge, ask for device, OS version and reproduction steps. Highly templated, low risk, high volume. This is where the real time saving lives. |
| `progress_lost` | `human_review` | Sounds like a bug but often is not. It is frequently the same underlying situation as `account_recovery`, described differently: the player is logged into a different account and does not realise it. An agent that confidently replies "we will restore your village" to what is actually an identity problem creates a promise the business may not be able to keep. |
| `purchase_missing` | `human_review` | Requires checking a receipt against a transaction log. The claim cannot be evaluated from the ticket text alone. An automated reply either promises a refund it has not verified or refuses one that is legitimate, and both are expensive. |
| `refund_request` | `hard_stop` | Money. There is no version of an automated reply about reversing a charge that is safe. It carries a consumer-protection dimension that varies by jurisdiction and app store, and where a minor's spending is involved it carries a legal one. |
| `account_recovery` | `hard_stop` | **The important one.** This category is identity verification wearing the costume of a support request. Every account takeover in a game starts with someone convincingly claiming to be the account owner. An LLM optimised to be helpful is exactly the wrong thing to put in that conversation, because the attacker's whole method is to sound like a distressed legitimate user, and that is the input the model is most agreeable towards. This is not a model quality problem that a better prompt fixes. It is a category that should not be automated at any accuracy level. |
| `abuse_report` | `hard_stop` | Player safety and, where minors are involved, a duty of care. Also frequently retaliatory or false, which requires judgement the agent does not have. The reputational cost of one badly handled abuse report is far larger than the labour saved across all of them. |

**Three of seven categories are refused. That is the point of the artifact.** Anyone can build the classifier. The reason to hire the person who built this one is that they drew the line before anyone made them.

---

## The confidence override

Whatever the category, if the model's confidence is below your threshold, the action becomes `human_review`. A confident wrong answer is worse than an unsure one, and the cheapest safety mechanism in the system is a number and a comparison.

Pick a threshold on Day 2 by looking at where your errors actually cluster, not in advance. Then write down what you picked and why, because that is a good interview answer.

---

## The ambiguous cases, and why they are in the dataset on purpose

Some tickets in `03-tickets.csv` genuinely belong to two categories. "I paid for the pack and it never came, I want my money back" is both `purchase_missing` and `refund_request`. This is not a flaw in the data, it is the actual condition of a support queue, and the resolution rule is the interesting part:

**When a ticket spans categories, the most restrictive action wins.**

That ticket is labelled `refund_request`, `hard_stop`. Not because refund is the better classification, but because the routing decision has to be the safe one. Make sure your prompt states this rule explicitly, and make sure you can say it out loud in an interview, because someone will hand you exactly this ticket and ask what your system does with it.

---

## What this policy is not

It is not a real support policy. A real one is written with legal, trust and safety, and finance in the room, and it would differ by market. This is a defensible engineering position taken by one person on synthetic data, and you should describe it that way. The strength of the claim is the reasoning, not the authority.
