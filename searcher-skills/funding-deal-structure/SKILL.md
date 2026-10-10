---
name: funding-deal-structure
description: Model how a small-business acquisition gets funded under the current SBA 7(a) rules — sources and uses, the 10% equity injection and what counts toward it, seller-note structures (full standby, amortising, interest-only, rollover equity), minority investor equity, debt service and DSCR, and the maximum price a structure supports. Use this whenever a self-funded searcher or buyer asks how to pay for a business, what an SBA loan would look like, whether a seller note can count as their down payment, how much cash they need, what DSCR means, how to structure seller financing, or "can I afford this at $X". Trigger it for any funding, financing, down-payment, or deal-structure question about buying a business.
---

# Funding & Deal Structure

A calculator plus a rulebook that is re-verified every time it runs. Nothing that moves is hard-coded: prime rate, guaranty fee, the searcher's salary need, working capital and closing costs are all passed in.

## Before running — three live lookups (every time)

1. **Current SOP version.** Web search "SBA SOP 50 10 current" and open sba.gov. Confirm the equity-injection and seller-note rules in `references/sba-rules.md` still hold. Two versions shipped within 18 months; assume drift.
2. **Guaranty fee.** Web search "SBA 7(a) guaranty fee" for the current fiscal year; compute the dollar fee for the expected loan size (it's charged on the guaranteed portion, typically 75% of the loan above $150k). Pass `--guaranty-fee`.
3. **Prime rate.** Fetch the Federal Reserve H.15 "bank prime loan" rate or an equivalent daily source. Pass `--prime`.

Then ask the searcher for the four numbers only they know: price (or asking price), SDE (seller's discretionary earnings, from the seller's numbers — note whose numbers they are), cash they can inject, and the salary they need to live on. If they don't have SDE yet, stop and say so — everything downstream is arithmetic on that number.

## Run

```bash
python scripts/deal_stack.py --price 900000 --sde 310000 --cash 120000 --salary 100000 --prime 6.75 \
  --working-capital 50000 --closing-costs 25000 --guaranty-fee 0 --compare
```

`--compare` prints three standard structures side by side (cash only; 10% full-standby seller note; 20% note with two interest-only years), each with sources & uses, debt service, DSCR, and the maximum price that structure supports at the DSCR floor. Drop `--compare` and pass `--seller-note / --seller-standby / --seller-rate / --seller-years / --seller-io-years / --minority-equity` to model the exact deal on the table. `--json` for machine-readable output.

## What the output means (say this in plain words)

- **Total project cost** is more than the price: working capital, closing costs, and the SBA fee are financed too, and the 10% injection is measured against the total.
- **Injection** is the searcher's unborrowed cash. A full-standby seller note can cover up to half of it; anything on partial standby covers none of it and now also counts against DSCR. That one rule change decides most structures.
- **DSCR** is cash available after the searcher's salary divided by debt service. Below 1.25 most lenders won't write it; below 1.15 nobody will. The "max price" line is the searcher's ceiling for that structure — the single most useful number in the output.
- **Cash left after debt and salary, year one** is what actually lands in their pocket. If it's thin, say so.

## Structures and negotiation

`references/structures.md` lists every structure the searcher is likely to meet, the seller's reason to accept it, and its SBA treatment, plus the negotiation posture [Voss]. Use it to explain *why* a full-standby note is worth more to the buyer than the seller usually thinks.

## Always say

This models a structure; it is not a lender's underwriting, legal advice, or tax advice. Rules were verified on the date in `references/sba-rules.md` and re-checked at run time; the lender's credit policy governs. If the searcher is not a U.S. citizen or permanent resident, SBA eligibility is the first question for a lender, before any of this.
