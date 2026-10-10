---
name: transition-signals
description: Score a list of long-established businesses for how ready they look to change hands — owner still operating, named successor or not, retirement language, and how old-school the web presence is — using only public evidence (the company website, state registry officers, SBA and Form 5500 facts, and web search). Use this whenever a self-funded searcher or buyer has a target list (typically survivors.csv from longevity-finder) and asks which ones to prioritise, which owners might be retiring, which businesses have no successor, which look "boomer-coded", or how to rank off-market targets. Trigger it for any prioritising or ranking of acquisition targets, even if they don't say "signals".
---

# Transition Signals

Turns a long list into a ranked shortlist, with the evidence beside every score. No API keys. Websites are fetched directly; everything else is already in the searcher's files or one web search away.

## Inputs

- `survivors.csv` from `longevity-finder` (or any CSV with `business_name`, ideally `officers`, `years_registered`, `headcount_5500`, `ppp_jobs`, `city`).
- A `website` column. It won't be there yet. Fill it:
  1. Add the column.
  2. For each of the top N targets (ask the searcher how many; 40–60 is a good first pass), use web search with the business name plus city and pick the business's own domain. Skip directories, Yelp, BBB, Facebook pages. If there's no own site, leave the cell blank — blank is a valid answer.
  3. Save the CSV.

## Run

```bash
pip install -r requirements.txt -q
python scripts/fetch_site.py --input survivors.csv --out site_signals.csv --limit 60
python scripts/score_signals.py --survivors survivors.csv --site site_signals.csv --out ranked_targets.csv
```

`fetch_site.py` pulls the home page plus up to four about/team/history pages per site, politely (one request per second), and extracts: founding year, years-in-business claims, family-owned and generation language, son/daughter mentions, retirement and transition words, owner-operated phrasing, hiring pages, booking widgets, analytics pixels, social links, copyright year, mobile-responsiveness, and whether a registry officer's surname appears on the site.

`score_signals.py` produces four scores per business, each with an evidence string:
- `owner_operated_score` — owner still central
- `named_successor_score` — somebody is already lined up (a *low* score is what the searcher wants)
- `retirement_signal_score` — transition language present
- `boomer_coded_score` — no pixels, no booking, no social, stale copyright, not mobile-responsive (higher = more old-school; blank when no site)

and a `transition_priority` that weights them: owner central × no successor × retirement cues × old-school presence.

## Then do the judgement pass (this is where it gets excellent)

The heuristics are deliberately dumb and visible. For the top 20–30 by `transition_priority`, read the evidence columns and the pages, and answer the three rubric questions in `references/rubric.md` with probabilities. Save to `judgements.csv` and re-run:

```bash
python scripts/score_signals.py --survivors survivors.csv --site site_signals.csv --judgements judgements.csv --out ranked_targets.csv
```

Two more public sources are worth a look for the top 10, by web search and fetch, no script needed:
- the BBB business profile (start date and principals, when one exists);
- the state licence board record (licence holder name and original issue date — Florida: the DBPR licence search), which tells you whether the licence sits with the owner personally, a key diligence fact.

Add what you learn to `notes` in `judgements.csv`.

## How to present it

Top 10 as a table: name, city, years, headcount, the three probabilities, one line of evidence each. Then the pattern across the list (how many owner-operated with no successor; how many already transitioned). Then the next step: `first-call-brief` for whichever ones the searcher wants to approach.

Say plainly what wasn't checked: no reviews were read (that needs an API or a scraper, neither of which this pack uses), and no personal information on any owner was gathered beyond public corporate filings.
