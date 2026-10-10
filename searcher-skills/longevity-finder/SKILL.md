---
name: longevity-finder
description: Find long-established businesses in one industry and one US state from public government data — SBA PPP and 7(a) loan files, the state corporate registry (charter date, FEI, officers), and DOL Form 5500 (headcount) — joined into a survivors.csv with a confidence score per row. Use this whenever a self-funded searcher, acquisition entrepreneur, or small-business buyer wants off-market targets, "businesses that have been around 20/30/40 years", owner-operated companies in a trade or service industry, a target list for a county or state, or asks how to find retiring owners. Trigger it for any request to build a list of businesses to approach, even if they don't mention data sources. Florida is fully supported today; other states stop at the SBA stage.
---

# Longevity Finder

Builds the searcher's target universe from public files, with the evidence behind every row. No API keys, no accounts, no scraping of protected sites.

## What comes back

`survivors.csv` — one row per business: name, city, charter date and years registered, SBA loan history (with a payroll estimate from PPP), Form 5500 headcount, up to six officers with titles, a family-surname flag, and a match score with the evidence string. Column meanings: `references/data-dictionary.md`.

`survivors_*_unmatched_sba.csv` — SBA borrowers in the industry that the registry match lost. Always mention this file and its row count; it is the honest measure of recall.

## Before running: three questions, answered in one line each

1. **State.** Only Florida has a registry adapter today (`references/state-coverage.md`). For any other state, say so plainly and offer the SBA-only pass (borrower name, city, NAICS, loan size, year — no charter date).
2. **Industry → NAICS.** Use `../market-mapper/references/naics-quick-list.md` or a web search. Confirm the code with the searcher.
3. **Thresholds.** Default: 30+ years, PPP loans of $150k+ (the SBA publishes those in one file; the under-$150k loans are twelve more large files — offer `--ppp-small` if the searcher wants smaller businesses).

## Run

```bash
pip install -r requirements.txt -q
cd scripts
python run_state.py --state FL --naics 238220 --min-years 30 --min-loan 150000 --mode both
```

Stages, each skipped on re-run if its output exists:
1. `fetch_sba.py` — discovers current file URLs via data.sba.gov's CKAN API, downloads the PPP $150k+ file and the 7(a) FOIA files, filters to state + NAICS.
2. `fetch_sunbiz.py` — downloads Florida's quarterly registry over the Division's public SFTP (credentials are published by the state; they're in `references/florida-sunbiz-layout.md`) and streams the ten fixed-width files into `sunbiz_active.csv`. This is the slow stage: roughly 17 GB downloaded, 20–40 minutes depending on connection. Tell the searcher before starting it. If their network blocks SFTP, they can download the files in a browser from the same portal and pass `--local-registry <folder>`.
3. `fetch_5500.py` — DOL Form 5500 and 5500-SF "Latest" datasets for the two most recent years, filtered to the state.
4. `build_survivors.py` — the join. Runs both modes by default:
   - **sba-first**: precise. Every row is an SBA borrower in the industry matched to a registry record.
   - **registry-first**: broad. Every active registry entity old enough whose name, Form 5500 business code, or SBA record says it's in the industry.
   Present sba-first as the shortlist and registry-first as the long list.

Expect the registry stage to take a while and the matching stage to take a few minutes.

## First-run checks (do these, don't skip)

- After the registry download, run `python fetch_sunbiz.py --sample data/raw/<one cordata file>` and look at the printed date-format detection and status-code distribution. If active entities aren't coded `A`, re-run with `--status <code>`.
- Open `*_unmatched_sba.csv`. If more than ~40% of SBA borrowers went unmatched, something is off — usually the registry file didn't fully parse, or the NAICS filter was too narrow. Fix before presenting results.
- Spot-check three rows by hand on the state's public search page (Florida: search.sunbiz.org) using `registry_doc_number`. Report what you found.

## How to present results

Lead with the counts: how many SBA borrowers in the industry, how many matched to the registry, how many are 30+ years, how many have a Form 5500 headcount. Then the top 15 by years registered, with city, headcount, and the officer line. Then the honest caveats:
- charter date is the registry's formation date, not necessarily founding year (re-incorporations look young);
- PPP payroll is a 2020-era estimate;
- Form 5500 only covers employers with a benefit plan — a blank headcount means "no plan filed", not "no employees";
- officer data is as fresh as the last annual report.

Then point to the next skill: `transition-signals` scores which of these look ready to hand over.

## What this skill refuses to do

It does not scrape search.sunbiz.org or any CAPTCHA-protected site, does not use people-search services, and does not pull personal data on owners beyond what the state registry publishes about corporate officers.
