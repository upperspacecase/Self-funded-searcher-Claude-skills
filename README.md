# Searcher Skills — a free pack for self-funded searchers

Five Claude Code skills that take a self-funded searcher from "which industry and county" to "how do I pay for it", using nothing but public data. No API keys. No accounts. No technical setup.

| Skill | One-line prompt that triggers it | What comes back |
|---|---|---|
| `market-mapper` | "Where are the plumbing businesses in Florida concentrated?" | County table: establishments, size bands, fragmentation |
| `longevity-finder` | "Find plumbing businesses in Florida that have been around 30+ years" | `survivors.csv` — name, city, charter date, years, SBA loan history, headcount, officers, match confidence |
| `transition-signals` | "Which of these look ready to hand over?" | `ranked_targets.csv` — owner-operated / successor / retirement / boomer-coded web presence, scored with evidence |
| `first-call-brief` | "Prep me for a call with Reed Service Co" | One-page brief + question bank |
| `funding-deal-structure` | "I can put in $120k, they want $900k, SDE is $310k — how does this get funded?" | Sources & uses, DSCR test, three structures side by side, current SBA rules |

## Install (once)

```bash
mkdir -p ~/.claude/skills
cp -r searcher-skills/* ~/.claude/skills/
```

Or drop the folders into `.claude/skills/` inside the project you run Claude Code from. Claude Code installs its own Python dependencies the first time a skill runs (`pip install -r requirements.txt` in each skill folder).

## Data sources (all public, all free)

- Florida Division of Corporations bulk registry — public SFTP, documented fixed-width layout, includes FEI/EIN and up to six officers per entity
- SBA Paycheck Protection Program FOIA files and SBA 7(a) FOIA loan files — data.sba.gov
- US Department of Labor Form 5500 / 5500-SF datasets — headcount via plan participants, NAICS via business code
- US Census County Business Patterns — establishment counts by county and size band
- Business websites and BBB profiles — fetched directly
- SBA SOP 50 10 8 / 8.1 and SBA rate notices — fetched live when the funding skill runs

## State coverage

The proof build is Florida. The pipeline is state-agnostic; each new state needs one registry adapter (see `longevity-finder/references/state-coverage.md`). Every skill tells the searcher up front whether their state is fully supported.

## Honest limits

- Name matching across government files is approximate. Every match carries a confidence score and the evidence used; nothing is silently merged.
- Registry officer data is as fresh as the last annual report.
- The funding skill models structures; it is not legal, tax, or lending advice, and it says so.
