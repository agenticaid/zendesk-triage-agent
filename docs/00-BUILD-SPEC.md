# Build Spec: Support Ticket Triage Agent

**Owner:** Erez Cohen
**Written:** 2026-09-01
**Purpose:** a portfolio asset that closes three named gaps against CX automation job descriptions (Zendesk, orchestration platforms, data literacy) in three working days.
**Not:** a product. There is no user, no real data, and no revenue. Everything below is designed so that it can be described honestly and still be impressive.

---

## 1. What you are building, in one paragraph

A ticket arrives in Zendesk from a player of a mobile game. An automation picks it up, an LLM reads it, decides which of seven categories it belongs to, and then either drafts a reply, flags it for a human, or refuses to touch it at all. The refusal is the interesting part. Everything gets tagged and logged so the whole run can be measured afterwards against a known correct answer.

That is it. Resist making it more.

---

## 2. Why this specific build

Every job description in this family asks for the same four things, and this one build evidences all four at once.

| What the JD asks for | What this build proves |
|---|---|
| Experience with Zendesk or Salesforce | You have configured a Zendesk instance and driven it through its API |
| Orchestration platforms (Make, Zapier, Torq) | Make is doing real work in the flow, not decoration |
| LLM APIs and prompt engineering | A classification and drafting prompt with a measured accuracy figure |
| Analyze support data, track KPIs | An evaluation script that produces a number and a confusion matrix |

The fifth thing, which is not in any JD but is what actually gets you the interview: the guardrail policy in `02-TAXONOMY-AND-GUARDRAILS.md`. Most people who build a triage demo automate everything they can. You are going to deliberately refuse to automate three categories, and be able to explain exactly why in terms of risk to the business. At a game company, account recovery is the account-takeover attack surface. An agent that auto-replies to "I lost access to my account" is a social-engineering vector. Knowing that without being told is the difference between a hobbyist and someone they can hire.

---

## 3. Hard constraint: the Zendesk clock

**The Zendesk trial is 14 days.** ([Zendesk Developer Docs](https://developer.zendesk.com/documentation/api-basics/getting-started/getting-a-trial-or-sponsored-account-for-development/))

Do not sign up until the morning you actually start Day 1. If you sign up tonight out of curiosity you will burn four days of the clock reading documentation.

There is a non-expiring "sponsored" developer account, but it is only for people building apps for the Zendesk Marketplace, so it does not apply to you. Same source.

Consequence: take screenshots of everything as you go. After 14 days the instance is gone and your README needs to still be able to show what you built.

---

## 4. Scope

### In

- One Zendesk trial instance, seeded with the ~90 synthetic tickets in `03-tickets.csv`
- Seven categories, three action levels (see `02-TAXONOMY-AND-GUARDRAILS.md`)
- One Python script that classifies a ticket, decides the action, and writes back a tag plus an internal note
- One Make scenario that connects Zendesk to that script
- One evaluation script that scores the run against the ground-truth labels in the CSV
- A README that a hiring manager can read in ninety seconds

### Out, explicitly

Write these on a sticky note. This is the list that decides whether this takes three days or three weeks.

- No multi-turn conversation. One ticket in, one decision out.
- No knowledge base, no RAG, no retrieval of any kind.
- No Hebrew. English only.
- No real customer data of any kind, ever.
- No CSAT, no deflection rate, no cost model. You have no users, so you have no such metrics.
- No custom UI. Zendesk's own interface is the UI.
- No fine-tuning.
- No handling of attachments or images.

---

## 5. Architecture

```
Zendesk (new ticket)
   |
   v
Make scenario  ---- watches for new tickets, sends id + subject + body
   |
   v
Python service on Cloud Run    ---- calls Claude API, gets {category, action, draft, confidence}
   |
   v
Make scenario  ---- writes back to Zendesk: tag, internal note, and the draft where allowed
   |
   v
Zendesk (ticket now tagged and routed)
```

Four notes on this.

**Why Make is in the middle and not just Python calling Zendesk directly.** Because the JD asks for orchestration platform experience and you need the claim to be true. Make is genuinely doing the triggering and the write-back here. If you cut it out, the build is weaker for your purposes even though it would be simpler code.

**Where to host it.** Use **Google Cloud Run**, not Railway.

Railway now gives $1 of credit a month after the first month, which is not enough to keep anything running, so the practical Railway option is the paid Hobby plan. Cloud Run's Always Free tier is 2 million requests a month, 360,000 GB-seconds of memory, 180,000 vCPU-seconds of compute, and 1 GB of outbound transfer, which is orders of magnitude more than 90 tickets will ever use. ([Google Cloud](https://docs.cloud.google.com/free/docs/free-cloud-features), [Render](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026) for the Railway figure, which is a competitor's page so treat it as indicative)

Two more reasons beyond the price.

First, Cloud Run is already the target architecture in your Enosh project. Using it here means your two AI builds share a deployment story instead of being three different stacks, and "I run my services on Cloud Run" is a better sentence in an interview than a list.

Second, it is the correct shape for this job: a container that receives an HTTP request, scales to zero when idle, and costs nothing while nothing is happening. That is what a webhook target should be.

The one piece of friction: Cloud Run's free tier requires a Google Cloud billing account, which means a card on file. Set a budget alert at a few dollars the moment you create the project. New accounts also get $300 of trial credit over 90 days, which is a separate thing from the Always Free tier and is not what you are relying on here.

**If you refuse to put a card down:** Render's free web service tier gives 750 instance hours a month, but it spins down after 15 minutes of inactivity and takes around a minute to wake. For a Make webhook that is a real problem, because the first call after idle will time out. Workable only if you add a scheduled ping to keep it warm, which is exactly the kind of workaround you would rather not have to explain. Fly.io no longer offers a free tier to new signups. Same Render source, same caveat about whose page it is.

**And the option you should consciously reject:** Make can call the Claude API directly with an HTTP module, no hosting at all. It would work. Do not do it, because the classification logic and the prompt would then live inside a Make scenario where they cannot be version controlled, tested, or shown in a repo. Being able to say why you rejected that is worth more than the hour it would save.

**Fallback if Make's Zendesk trigger will not work on a trial account.** Do not fight it. Replace the trigger with a Make scheduled HTTP module that polls the Zendesk search API every 5 minutes for tickets without your tag. Functionally equivalent for a demo, and being able to say "the webhook path was not available on trial so I polled instead" is a normal engineering answer.

**Confidence.** Have the model return a confidence value and treat anything below your threshold as human review regardless of category. This gives you a second dial to talk about in an interview and it is two lines of code.

---

## 5.1 What needs Zendesk, and what does not

Read this before starting anything, because it decides when you open the trial.

Most of the work in this build never touches Zendesk. The prompt, the classification script, the evaluation script, the accuracy figure and the error analysis all run straight off `03-tickets.csv`. Zendesk is needed for exactly three things: seeding the tickets, writing tags and internal notes back, and the Make scenario that connects them.

| Step | Needs Zendesk? |
|---|---|
| Reading the primer | No |
| Testing the prompt by hand | No |
| Classification script, CSV in, JSON out | No |
| Evaluation script, accuracy, confusion matrix, error analysis | No |
| Seeding the 90 tickets | Yes |
| Writing tags and internal notes back | Yes |
| Make scenario | Yes |
| Screenshots for the README | Yes |

So do the whole left-hand column first and open the trial only when you are ready to wire things up. Two reasons. It protects the 14-day clock, which is the only genuinely scarce resource in this project. And it is better engineering regardless, because it forces the classification logic to be independent of the integration rather than tangled into it.

The practical consequence is that the plan below is written as three days, but the Zendesk trial is not opened until partway through Day 2.

## 5.2 Honest time estimate

The real work is roughly nine to eleven hours, not three full days:

| Block | Time |
|---|---|
| Reading the primer properly | 45 min |
| Testing the prompt by hand on ten tickets | 25 min |
| Classification script | 1 to 1.5 hr |
| Evaluation script, running it, and the error analysis | 1.5 to 2 hr |
| Zendesk setup and seeding the tickets | 45 min |
| Write-back, Make scenario, Cloud Run deploy | 2 to 3 hr |
| README and screenshots | 1.5 hr |

It is split across three days because the error analysis and the first Cloud Run deploy are the two things that reliably take longer than planned, not because any day is full. Six blocks of two hours gets you the same result.

## 6. The three-day plan

### Day 1: Zendesk and the taxonomy

Morning. Sign up for the trial. Work through `01-ZENDESK-PRIMER.md` end to end so the object model is not mysterious. Create your API token. Confirm you can create and read one ticket from Python.

Afternoon. Write the seeding script and load all ~90 tickets from `03-tickets.csv`. Then read twenty of them in the Zendesk agent interface as a support agent would. This matters more than it sounds: you are about to write a prompt about a job you have never done, and twenty minutes of looking at the queue the way an agent sees it will change how you write it.

Evening, optional but strongly recommended. Test the prompt by hand before writing any code. By hand means literally this: open claude.ai in a browser, paste the classification prompt from `04-AGENT-PROMPT.md` into the message box, replace `{{subject}}` and `{{body}}` with a real ticket from the CSV, and send it. Read the JSON that comes back and compare it to that ticket's `ground_truth_category` column. Do that for ten tickets, picking a mix that includes at least three of the ambiguous ones (T033, T035, T046, T007).

No API, no script, no Zendesk. Just the chat window and the CSV open next to it, ten times, about twenty minutes.

The reason to do it this way is that a prompt fault and a code fault look identical once there is code in between. If you find out at this stage that the model calls T033 `purchase_missing` instead of `refund_request`, you know for certain the rule is not landing, and you fix one paragraph of English. Discovering the same thing tomorrow through a failing test run costs you an hour of looking in the wrong place.

**Done when:** ~90 tickets are visible in your Zendesk queue and you have classified ten of them by hand with the prompt.

### Day 2: The agent and the measurement

Morning. Write the triage script. It should be one file. Input: a ticket id or a raw subject and body. Output: a JSON object with category, action, confidence, and draft. Nothing else.

Afternoon. Write the evaluation script. Run the agent over all ~90 tickets, compare to the ground truth column, print accuracy overall and per category, and print a confusion matrix. Then look at every single mistake and decide whether the prompt is wrong or the label is wrong. Sometimes it will be the label. Fix and rerun.

**Done when:** you have a number, and you have looked at every error individually.

**Stop rule:** two prompt iterations, then stop. If accuracy is 82 percent, that is a fine, honest, defensible number and chasing 90 will cost you Day 3. A candidate who reports 82 percent and can explain exactly which categories confuse each other is more convincing than one who reports 96 and cannot.

### Day 3: The flow and the write-up

Morning. Deploy to Cloud Run. Build the Make scenario. Test it on one live ticket you create by hand and watch the tag appear.

Afternoon. The README, from `05-README-TEMPLATE.md`. Screenshots: the Zendesk queue with your tags visible, the Make scenario canvas, the confusion matrix, and one hard-stop ticket showing the internal note explaining why the agent refused. Record a 30-second screen capture of one ticket going through end to end.

**Done when:** someone who has never seen the project can read the README and understand what you built and what it does not do.

---

## 7. Definition of done

The build is finished when all six are true. Not five.

1. ~90 tickets sit in a real Zendesk instance, tagged by the agent.
2. You can state one accuracy number and explain the errors behind it.
3. **Zero hard-stop tickets received an auto-draft.** This is pass or fail, not a percentage. One miss and the guardrail does not work. See section 7.1 for exactly what counts as a miss.
4. The Make scenario runs end to end on a ticket created after the fact.
5. The README exists and labels the data as synthetic in the first paragraph.
6. Screenshots are saved locally, because the trial will expire.

---

### 7.2 The confidence figure, and checking whether it means anything

The `confidence` value the model returns is a self-report, not a probability. The model is not reading out an internal likelihood over the seven categories; it is generating a number as text, the same way it generates every other token. Self-reported confidence from language models is usually poorly calibrated, clusters in a narrow high band, and moves with prompt wording.

The round 1 results show the shape of the problem: nine of ten values landed between 0.85 and 0.97, with 0.85 appearing three times. That is a small set of conventional-sounding numbers, not a continuous estimate.

It is still worth keeping, because it carries **ordinal** information even when the absolute value is meaningless. The one ticket the model rated 0.70 was the one genuinely ambiguous ticket in the set. That is a real signal. What is not justified is treating 0.75 as a boundary with statistical meaning.

**So measure it. You already have everything you need.** You have 90 ground-truth labels and you are already running an evaluation, so bucket the tickets by reported confidence and compute the actual accuracy in each bucket:

| Reported confidence | Tickets | Actual accuracy |
|---|---|---|
| below 0.75 | | |
| 0.75 to 0.89 | | |
| 0.90 and above | | |

If accuracy rises across the buckets, the number is informative and your threshold is doing real work. If it is flat, the number is decoration and you should say so plainly in the README and treat rule 3 as a cheap extra rather than a safety mechanism. Ninety tickets across three buckets is enough to see a direction and not enough for a statistical claim, so report it as a direction.

This check costs almost nothing and it is one of the most convincing things you can put in the README. Reporting a confidence figure is ordinary. Reporting whether it turned out to mean anything is not.

**The alternative, if you want a confidence figure with a real basis:** run each ticket three or five times at a non-zero temperature and use the level of agreement between runs as the confidence. Five identical answers is genuinely strong evidence; three out of five is genuinely weak. It is empirical rather than self-reported, and it costs three to five times the tokens. Worth doing for the `hard_stop` categories alone if you want the safety claim to rest on something firmer, and worth mentioning in an interview whether or not you implement it.

The other route, reading token-level log probabilities to get the model's actual distribution over the category choice, is not available here: the Claude API does not expose logprobs natively, and the workarounds are third-party approximations ([anthropic-logprobs](https://github.com/anerli/anthropic-logprobs)). Knowing why you cannot use that route is itself a good answer.

### 7.1 The three kinds of error, and what each one costs

Not all misclassifications are the same, and the evaluation script should separate them. This is also the framework for the "where it gets things wrong" section of the README.

Define the action order as `auto_draft` < `human_review` < `hard_stop`, from least to most restrictive.

**Safety failure.** A ticket whose true action is `hard_stop` that the system routed to `auto_draft`. In other words, an account recovery, refund, or abuse ticket that the model read as a gameplay question or a bug report, and then wrote a reply for. **This count must be zero.** Not low, zero. Report it as a count, never as a percentage or a recall figure: "99 percent recall on hard-stop cases" sounds respectable and describes a system where one in a hundred account-takeover attempts gets an automated helpful reply. That is a security incident, not a rounding error.

Note what this is *not*. A `hard_stop` ticket that the model misfiled as `progress_lost` and sent to `human_review` is a classification error, and you should count and report it, but it is not a safety failure. Nothing was drafted and a person still handles the ticket. That is precisely why there are three action levels instead of two: the middle level absorbs the model's mistakes.

**Under-routing.** Any other case where the assigned action is less restrictive than the true one. Mostly this will be `human_review` tickets that got a draft, for example a `purchase_missing` read as a `bug_report`. Real cost, but bounded: an agent reads a draft that does not fit and discards it. Track the number and look at what caused it.

**Over-routing.** The assigned action is more restrictive than the true one. A `gameplay_question` sent to human review, a `bug_report` hard-stopped. The cost is wasted human time and less automation than you could have had. **This is the direction you want your errors to fall in**, and reporting the figure openly is what shows you understand the trade you made rather than having stumbled into it.

Two tickets in the dataset are the ones most likely to produce a genuine safety failure, and they are there on purpose: **T007** ("the facebook button does nothing and if i play as guest i get a new empty game") and **T009** ("after the update it logged me out ... two of my friends have the same problem"). Both are `account_recovery` written in the vocabulary of a bug report. If your system drafts a reply to either of those, you have found the real weakness of the design, and fixing it is more valuable than two points of overall accuracy.

## 7.3 Deliverable: the context page

A second artifact, separate from the README, published as an HTML page.

The README answers "what did you build and does it work". This page answers "what did you think the world looked like when you built it". They are different documents for different readers and merging them ruins both.

### The rule that decides the whole tone

Erez has never worked in a support organisation. A page that confidently explains how support organisations work will be read by people who have worked in them, and it will read as bluffing. One question undoes it.

So the page is never "here is how support works". It is **"here are the assumptions I designed against, and here is what I would need to verify with your team before a line of this reached production."**

That framing is not a hedge, it is the stronger version. Every experienced engineer joining a new domain starts by writing down their assumptions and getting them corrected. Showing that you do that is a competence signal. Pretending you already know is the only move that can actually lose you the interview.

Mark every claim on the page as one of three things: something you verified and can cite, something you assumed and would check, or something you deliberately excluded from scope. If a claim will not fit into one of those three boxes, it does not go on the page.

### Structure

**1. The problem this sits inside.** Not the triage agent. The support queue: what arrives, why the volume is spiky in a live game rather than steady, and what a human agent's day actually consists of.

**2. The assumptions I designed against.** The core of the page. Each one stated plainly, with what changes in the design if it turns out to be wrong. This is the section that shows engineering judgement rather than engineering output.

**3. The ecosystem the agent lives in.** What else is in the room: the other systems, the other people, the metrics that are already being measured and who owns them.

**4. Why three action levels and not two.** The `human_review` versus `hard_stop` distinction, framed as "not yet" against "not ever". The strongest single idea in the project and it deserves its own section.

**5. What the agent cannot see.** It reads ticket text. It has no access to the account, the transaction log, the telemetry, or the player's history. Everything the design gets right follows from being honest about that, and it is the reason `purchase_missing` cannot be automated.

**6. How this would actually be deployed.** The ladder in the next section. This is the part that separates someone who has built a demo from someone who has thought about shipping.

**7. What I do not know.** Named, specifically. Ends the page.

### The content you need to learn, which is the same as the content of the page

Erez does not currently hold most of this. Treat the list as a study plan, not a summary. Verify each item before it is published.

**Who is actually in a support organisation.** Tier one agents handling volume with canned responses, often outsourced and often covering 24 hours for a global player base. Specialist tiers for billing, account security, and trust and safety. Team leads. QA analysts who score a sample of tickets against a rubric. Workforce management, which forecasts volume and staffs against it. And support operations, the people who own the CRM configuration, the macros, the triggers and the integrations. That last group is the seat this JD describes.

**The metrics, and the fact that they fight each other.** First response time, full resolution time, SLA compliance, CSAT, backlog, cost per ticket, and the gaming-specific one, contacts per thousand daily active users. Deflection rate is the metric an automation project is judged on. The thing worth understanding is that pushing deflection up too hard pushes CSAT down, so anyone who talks about deflection without mentioning that trade has not run one of these.

**Why game support volume is spiky rather than smooth.** Releases, live events, server incidents and store outages. Volume in a live game is event-driven, which changes what an automation is for: it is capacity during a spike, not a steady percentage saving.

**The systems next to the ticket.** The CRM is the front door, but a human agent also has an internal account admin tool, the transaction and receipt system, game telemetry, and the moderation tooling. An agent that reads only ticket text is blind to every one of those. Name that limitation on the page rather than letting a reader discover it.

**The money structure of a free-to-play game.** A small fraction of players pay, and a small fraction of those account for a large share of revenue. High-spending players are often routed to a separate support path. That is directly relevant to triage and worth asking about rather than assuming.

**The compliance surround.** App store refund policy, and specifically that the store often handles the refund rather than the studio, which is why refund tickets are more complicated than they look. Consumer protection rules on minors' spending. Data deletion requests that arrive through the support queue rather than through a legal channel. Age gating.

**The deployment ladder, which belongs on the page in full.** Shadow mode first: the agent runs silently against live tickets for weeks, its output visible to nobody, compared against what humans actually did. Then internal notes visible to agents. Then drafts an agent approves before sending. Then, only for the narrowest categories and only with data behind it, auto-send. Most demos skip straight to the last rung in their imagination. Naming the ladder is what shows you would not.

**The organisational reality.** Agents worry about being replaced, so adoption depends on the tool making their shift easier rather than on it being accurate. QA and legal hold effective veto power. The support director is thinking about cost and CSAT while the person building the agent is thinking about accuracy, and those are two different conversations that have to be held in the same room.

### Verification before publishing

Do not publish this page on the strength of a model's summary of an industry, this one included. Before it goes up: read two or three first-hand accounts from people who have worked in game support or support operations, and if you can, ask one person who has. A single conversation with someone who has run a support queue will correct more of this page than an hour of reading.

Anything still unverified moves to section 7, "what I do not know". That section being long is a feature.

### Format

Self-contained HTML, published as an artifact so it has a URL and can be linked from the CV and the README. It is a page someone reads once and it needs to survive being read by an expert, so plain prose and clear structure beat visual decoration. One diagram earns its place: the deployment ladder.

## 8. How you will describe this, honestly

Use this wording. It is the strongest version that is also true.

> Built a ticket triage agent on a Zendesk instance seeded with ~90 synthetic mobile-game support tickets. Classifies into seven categories and routes by risk: low-risk categories get a drafted reply, ambiguous ones go to human review, and three categories including account recovery and refunds are hard-stopped from any automated reply. Orchestrated through Make, agent on Google Cloud Run, classification accuracy measured against labelled ground truth.

Words that must never appear next to this project: deflection rate, production, deployed to customers, CSAT, cost savings, users. You have none of those and the first person who asks will find out in one question.

Word that must always appear: synthetic.

---

## 9. Files in this folder

| File | What it is | When you need it |
|---|---|---|
| `00-BUILD-SPEC.md` | This file. The plan and the guardrails on scope. | Read once, then reread the Out-of-scope list whenever you feel like adding something |
| `01-ZENDESK-PRIMER.md` | Zendesk from zero. Concepts, click paths, the API calls you need. | Day 1 morning |
| `02-TAXONOMY-AND-GUARDRAILS.md` | The seven categories and the risk policy. The interview artifact. | Day 1, and again when writing the README |
| `03-tickets.csv` | ~90 synthetic tickets with ground-truth labels | Day 1 afternoon |
| `04-AGENT-PROMPT.md` | The system prompt, ready to use | Day 1 evening and Day 2 |
| `05-README-TEMPLATE.md` | The README skeleton with the numbers left blank | Day 3 |
| `06-PROMPT-LOG.md` | Pre-filled test table for the ten hand tests, plus the change log | The moment you start testing the prompt |
| `07-PROMPT-VERSIONS.md` | Every prompt version kept verbatim | Whenever you change a prompt |
| `08-CONTEXT-PAGE.html` | The context page specified in 7.3. Not written yet | After the build works, before applying anywhere |
| `CLAUDE.md` | Project context so Claude Code has it without you re-explaining | Sits in the repo root, you never read it |

Everything you need is here. If you find yourself needing to come back and ask me for something, that is a gap in this spec and worth telling me about.
