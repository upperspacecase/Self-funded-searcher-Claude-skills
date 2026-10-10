---
name: market-mapper
description: Map where an industry's small businesses are concentrated inside a US state, county by county, using Census County Business Patterns — establishment counts, size bands, and a fragmentation read. Use this whenever a self-funded searcher or small-business buyer asks where to hunt, which county or metro has the most targets, how fragmented an industry is, "how many plumbers/HVAC/landscapers are there in X", or wants to pick a geography before sourcing. Trigger it even if they just name an industry and a state and ask where to start.
---

# Market Mapper

Answers the searcher's first question — *where are the businesses I want to buy?* — with public Census data, no key required.

## What it produces

A county table for one industry (NAICS code) in one state:

- establishments (all sizes)
- establishments by employment band (<5, 5–9, 10–19, 20–49, 50–99, 100+)
- share of establishments with fewer than 20 employees (the "fragmentation" read)
- the state total, so each county's share is obvious

Plus a short written read: which counties hold the density, whether the industry is fragmented enough for a roll-up or a single acquisition, and what the searcher should do next (usually: run `longevity-finder` on the top two or three counties).

## How to run it

1. Resolve the industry to a NAICS code. If the searcher gives a plain-English industry, look it up in `references/naics-quick-list.md` first; if it isn't there, use a web search for "NAICS code <industry>" and confirm the 6-digit code with the searcher in one line.
2. Run the script. It needs no key. The Census API allows a few hundred keyless calls a day, which is far more than this needs.

```bash
pip install -r requirements.txt -q
python scripts/cbp_pull.py --state FL --naics 238220 --out market_FL_238220.csv
```

`--state` accepts a two-letter postal code. `--naics` accepts 2–6 digits (a 4-digit code maps the whole sub-industry). Add `--year 2022` only if the latest vintage fails; the script tries the newest two vintages and both NAICS variable names on its own.

3. Read the CSV and write the summary. Lead with the three densest counties and the fragmentation percentage. Keep it to one screen.

## Interpreting the numbers

- CBP counts *establishments* (locations), not companies. A 40-truck HVAC company with two depots is two rows.
- Counts under a suppression threshold show as blank or 0 in the size bands even when the total is nonzero. Say so when it happens rather than treating a blank as zero.
- Fragmentation above ~80% under 20 employees is typical of trades and personal services. That is the profile buyers call "roll-up-able". Lower fragmentation means fewer, larger targets and more competition from institutional buyers.
- Density is a proxy for *supply of targets*, not for *willingness to sell*. The next skill handles that.

## What this skill does not do

It does not name specific businesses — that is `longevity-finder`. It does not size revenue; CBP has payroll but not sales, and payroll is a rough proxy at best. If the searcher asks for revenue, say that CBP doesn't carry it and move on.
