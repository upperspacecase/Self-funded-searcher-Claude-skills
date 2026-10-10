# SBA 7(a) rules the calculator encodes — and how to re-verify them before every use

Rules move. Two SOP versions landed in 18 months. Before presenting numbers, fetch the current state of each item below and update the arguments you pass to the script. Nothing in this file should be trusted as current without that check.

## Encoded rules, with the source they were verified against on 10 Oct 2026

| Rule | Value encoded | Verified against | Re-verify at |
|---|---|---|---|
| Minimum equity injection, complete change of ownership | 10% of total project cost | SOP 50 10 8 (effective 1 Jun 2025) as summarised by Live Oak Bank, Starfield & Smith, Whiteford Law | sba.gov → "SOP 50 10" current version; search "equity injection change of ownership" |
| Seller note credit toward injection | Only on **full standby for the life of the SBA loan**, and no more than **50% of the required injection** (5% of project on a 10% requirement); documented on SBA Form 155 | Same sources | Same |
| Limited sources of injection | Standby debt, full-standby seller debt, and equity from non-controlling minority investors (<20%, no control) — credited up to the 50% cap | SOP 50 10 8.1 (issued 14 Aug 2026, effective 1 Oct 2026) as reported by a secondary source (beancount.io). **Confirm against the SBA notice itself.** | sba.gov → SOP 50 10 8.1 and the issuing Procedural Notice |
| Seller debt in DSCR | Seller debt **not** on full standby is included in the lender's DSCR at a maximum 10-year amortisation | Same secondary source — **confirm** | Same |
| Personal guarantees | Partial change of ownership: all equity holders guarantee for at least two years, seller included if they retain equity. Complete change: investors under 20% need not guarantee | Whiteford Law client alert on SOP 50 10 8 | Same |
| Partial change of ownership, lower injection | Allowed below 10% if debt-to-worth is no greater than 9:1 before the change | Starfield & Smith | Same |
| Maximum variable-rate spreads over base | ≤$50,000: +6.5; $50,001–$250,000: +6.0; $250,001–$350,000: +4.5; >$350,000: +3.0 | SBA Procedural Notice 5000-875051 (via NAGGL), NerdWallet, Bankrate, sba7a.loans | sba.gov → "7(a) maximum interest rates" |
| Base rate | Prime (first business day of the month); alternative base rates permitted since 1 Mar 2026 with the same caps | Starfield & Smith, Feb 2026 | Look up prime live: Federal Reserve H.15 "Bank prime loan" or the WSJ prime rate |
| Maximum loan | $5,000,000 | SBA program page | sba.gov |
| Guaranty fee | **Changes every fiscal year.** FY2026 sources disagree at the margin ($950k vs $1M no-fee threshold). Pass `--guaranty-fee` in dollars from the current fee notice; the script does not guess | — | sba.gov → "7(a) fees" current notice |
| DSCR threshold | Script default 1.25 (common lender underwriting). SBA's own minimum coverage for the lender's credit memo may differ; the lender's number governs | lender practice | Ask the lender |

## What is NOT encoded (and why)
- Earn-outs: historically not financeable in a 7(a) change of ownership. Check the current SOP before telling a searcher either way.
- Seller rollover equity: allowed in a partial change of ownership with the guarantee consequences above; the calculator models the injection side only.
- Citizenship/ownership eligibility: the SOP tightened rules for non-U.S. owners. If the searcher isn't a U.S. citizen or LPR, flag it as the first question for a lender.
- Collateral: SOP 50 10 8 reset collateral rules. Not modelled.

## How to re-verify in Claude Code, in order
1. Web search "SBA SOP 50 10 current version" → open the sba.gov document page → note the version and effective date.
2. Web search "SBA 7(a) guaranty fee FY<current year>" → open the SBA notice → read the fee for the loan size.
3. Fetch the prime rate from the Federal Reserve H.15 release (or a reputable daily source) → pass `--prime`.
4. If anything differs from the table above, say so in the answer and pass the corrected values.
