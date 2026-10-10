---
name: first-call-brief
description: Prepare a self-funded searcher for a first conversation with a business owner — a one-page brief of everything public about the company, an opening line, questions in SPIN order (situation, problem, implication, need-payoff), what to listen for, and red flags to probe. Use this whenever a searcher says they have a call, meeting, or coffee with an owner, asks what to ask a seller, wants to prep for an outreach reply, or asks how to open a conversation about buying a business. Trigger it even if they only say "I'm meeting the owner of X on Thursday."
---

# First-Call Brief

One page the searcher can read in the car park. Built from `ranked_targets.csv` (or `survivors.csv`) plus the question bank; nothing is fetched at this stage.

## Run

```bash
pip install -r requirements.txt -q
python scripts/build_brief.py --targets ranked_targets.csv --name "Advent Air" --out brief_advent.md
```

If the searcher has notes from a reply (an email, a voicemail), paste the gist under "What the signals say" by editing the markdown — the brief is theirs to mark up.

## What's in it, and why

- **Public facts table** — so they never ask something the state already told them. Asking an owner "how long have you been in business?" when the registry says 1984 wastes the one thing a first call has: credibility.
- **What the signals say** — the scores and evidence from `transition-signals`, so they walk in knowing whether the owner is the business and whether there's an heir.
- **What I don't know yet** — the list of things no public record carries (revenue, SDE, the lease, the licence holder, whether they're a seller at all). This is the real agenda.
- **Opening** — one honest sentence: not a broker, one person, one business, no agenda beyond hearing how they built it.
- **Questions in SPIN order** — from `references/question-bank.md`. [Rackham, *SPIN Selling*; Ruback & Yudkoff, *HBR Guide to Buying a Small Business*.] Tell the searcher to ask the first three and then shut up; the rest are for when the owner is talking.
- **Listen for** — the tells that separate passive from active sellers.
- **Red flags** — only ones the data actually raised.

## Coaching the searcher, briefly

This is a listening call. No numbers, no structure talk, no "what would you want for it" — that's the second call and `funding-deal-structure`. If the owner raises price, the right answer is "I'd want to understand the business properly before I'd put a number near it — would you be open to showing me the last three years?"
