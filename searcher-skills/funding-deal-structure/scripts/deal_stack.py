#!/usr/bin/env python3
"""Sources & uses, debt service and DSCR for a small-business acquisition under the
current SBA 7(a) rules, with seller-note structures compared side by side.

Nothing here is hard-coded that moves: pass --prime from a live lookup, pass the
guaranty fee from SBA's current fee notice, pass the salary the searcher needs.
Rules encoded (see references/sba-rules.md for sources and what to re-verify):
  - minimum equity injection 10% of total project cost (SOP 50 10 8)
  - seller note counts toward injection only on FULL standby for the loan's life,
    and Limited sources (standby seller debt + non-controlling minority equity)
    are credited up to 50% of the required injection (SOP 50 10 8 / 8.1)
  - seller debt NOT on full standby is included in DSCR at <=10-year amortisation (SOP 50 10 8.1)
  - 7(a) maximum variable spreads over the base rate by loan size

Usage:
  python deal_stack.py --price 900000 --sde 310000 --cash 120000 --salary 100000 --prime 6.75 \
      --working-capital 50000 --closing-costs 25000 --guaranty-fee 0 \
      --seller-note 90000 --seller-standby full --seller-rate 6 --seller-years 10
  python deal_stack.py ... --compare        # three standard structures side by side
  python deal_stack.py ... --json           # machine-readable
"""
import argparse, json, math

MAX_SBA_LOAN = 5_000_000
SPREADS = [(50_000, 6.5), (250_000, 6.0), (350_000, 4.5), (float('inf'), 3.0)]  # SBA maximums, variable rate

def max_spread(loan):
    for cap, sp in SPREADS:
        if loan <= cap:
            return sp
    return 3.0

def annual_payment(principal, annual_rate_pct, years):
    if principal <= 0 or years <= 0:
        return 0.0
    r = annual_rate_pct / 100 / 12
    n = int(round(years * 12))
    if r == 0:
        return principal / years
    m = principal * r / (1 - (1 + r) ** -n)
    return m * 12

def structure(price, sde, cash, salary, prime, *, working_capital=0, closing_costs=0, guaranty_fee=0,
              seller_note=0, seller_standby='none', seller_rate=0.0, seller_years=0, seller_io_years=0,
              minority_equity=0, equity_pct=0.10, dscr_min=1.25, term_years=10, spread=None, rate=None, label=''):
    f = {}
    project = price + working_capital + closing_costs + guaranty_fee
    required_injection = equity_pct * project
    standby_credit_pool = (seller_note if seller_standby == 'full' else 0) + minority_equity
    limited_credit = min(standby_credit_pool, 0.5 * required_injection)
    cash_needed = max(required_injection - limited_credit, 0)
    if cash < cash_needed:
        f['equity_shortfall'] = f"buyer cash ${cash:,.0f} is below the ${cash_needed:,.0f} of unborrowed cash the 10% injection needs after Limited-source credit"
    buyer_cash = min(cash, cash_needed) if cash < cash_needed else cash_needed
    bank_loan = project - buyer_cash - seller_note - minority_equity
    if bank_loan > MAX_SBA_LOAN:
        f['over_sba_cap'] = f"bank loan ${bank_loan:,.0f} exceeds the $5,000,000 7(a) maximum"
    if seller_standby == 'full' and seller_note > 0.5 * required_injection:
        f['seller_note_over_credit'] = f"only ${0.5 * required_injection:,.0f} of the ${seller_note:,.0f} full-standby note earns injection credit; the rest still reduces the bank loan"
    sp = spread if spread is not None else max_spread(bank_loan)
    bank_rate = rate if rate is not None else prime + sp
    bank_ds = annual_payment(bank_loan, bank_rate, term_years)
    # seller note service
    if seller_note <= 0 or seller_standby == 'full':
        seller_ds_actual = 0.0; seller_ds_counted = 0.0
        if seller_note > 0:
            f['standby_note'] = "full-standby note: no principal or interest payments for the life of the SBA loan; confirm with the lender whether interest accrues"
    else:
        amort_years = max(seller_years - seller_io_years, 1)
        if seller_io_years > 0:
            seller_ds_actual = seller_note * seller_rate / 100  # year-1 interest only
            f['partial_standby'] = f"interest-only for {seller_io_years} year(s) then amortising over {amort_years}; year-1 cash cost shown"
        else:
            seller_ds_actual = annual_payment(seller_note, seller_rate, seller_years)
        # SOP 50 10 8.1: counted in DSCR at no more than 10-year amortisation
        seller_ds_counted = annual_payment(seller_note, seller_rate, min(seller_years if seller_years else 10, 10))
        f['seller_note_in_dscr'] = f"non-standby seller debt counted in DSCR at ${seller_ds_counted:,.0f}/yr (<=10-yr amortisation)"
    cash_flow_available = sde - salary
    total_ds_counted = bank_ds + seller_ds_counted
    dscr = cash_flow_available / total_ds_counted if total_ds_counted else float('inf')
    if dscr < dscr_min:
        f['dscr_below_min'] = f"DSCR {dscr:.2f} below the {dscr_min:.2f} threshold"
    cash_after_debt = cash_flow_available - bank_ds - seller_ds_actual
    return {
        'label': label, 'price': price, 'working_capital': working_capital, 'closing_costs': closing_costs, 'guaranty_fee': guaranty_fee,
        'total_project_cost': project, 'required_injection_10pct': required_injection, 'limited_source_credit': limited_credit,
        'buyer_cash_in': buyer_cash, 'seller_note': seller_note, 'seller_standby': seller_standby, 'minority_equity': minority_equity,
        'bank_loan': bank_loan, 'bank_rate_pct': bank_rate, 'bank_spread_pct': sp, 'term_years': term_years,
        'bank_debt_service': bank_ds, 'seller_debt_service_actual_yr1': seller_ds_actual, 'seller_debt_service_counted': seller_ds_counted,
        'sde': sde, 'owner_salary': salary, 'cash_flow_available': cash_flow_available, 'dscr': dscr, 'dscr_min': dscr_min,
        'cash_after_debt_and_salary_yr1': cash_after_debt, 'flags': f,
    }

def max_price_at_dscr(base_kwargs, dscr_min):
    """Bisection on price holding the structure's proportions (seller note as % of price) constant."""
    note_pct = (base_kwargs.get('seller_note', 0) / base_kwargs['price']) if base_kwargs['price'] else 0
    lo, hi = 0.0, base_kwargs['price'] * 4
    for _ in range(60):
        mid = (lo + hi) / 2
        kw = dict(base_kwargs); kw['price'] = mid; kw['seller_note'] = mid * note_pct
        if structure(**kw)['dscr'] >= dscr_min:
            lo = mid
        else:
            hi = mid
    return lo

def fmt(res):
    m = lambda v: f"${v:,.0f}"
    lines = [f"== {res['label'] or 'Structure'} ==",
             f"Uses: price {m(res['price'])} + working capital {m(res['working_capital'])} + closing {m(res['closing_costs'])} + SBA guaranty fee {m(res['guaranty_fee'])} = {m(res['total_project_cost'])}",
             f"Required injection (10%): {m(res['required_injection_10pct'])} | Limited-source credit: {m(res['limited_source_credit'])} | buyer cash in: {m(res['buyer_cash_in'])}",
             f"Sources: bank loan {m(res['bank_loan'])} @ {res['bank_rate_pct']:.2f}% (prime + {res['bank_spread_pct']}) over {res['term_years']}y | seller note {m(res['seller_note'])} ({res['seller_standby']} standby) | minority equity {m(res['minority_equity'])} | cash {m(res['buyer_cash_in'])}",
             f"Debt service: bank {m(res['bank_debt_service'])}/yr | seller counted {m(res['seller_debt_service_counted'])}/yr (actual yr1 {m(res['seller_debt_service_actual_yr1'])})",
             f"SDE {m(res['sde'])} - salary {m(res['owner_salary'])} = {m(res['cash_flow_available'])} available -> DSCR {res['dscr']:.2f} (min {res['dscr_min']:.2f}) | cash left after debt + salary yr1: {m(res['cash_after_debt_and_salary_yr1'])}"]
    for k, v in res['flags'].items():
        lines.append(f"  ! {k}: {v}")
    return '\n'.join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--price', type=float, required=True); ap.add_argument('--sde', type=float, required=True)
    ap.add_argument('--cash', type=float, required=True, help='unborrowed cash the buyer can inject')
    ap.add_argument('--salary', type=float, required=True, help='owner salary the buyer must draw before debt service')
    ap.add_argument('--prime', type=float, required=True, help='current prime rate, looked up live')
    ap.add_argument('--working-capital', type=float, default=0); ap.add_argument('--closing-costs', type=float, default=0)
    ap.add_argument('--guaranty-fee', type=float, default=0, help='SBA guaranty fee in dollars from the current fee notice')
    ap.add_argument('--seller-note', type=float, default=0); ap.add_argument('--seller-standby', choices=['full', 'partial', 'none'], default='none')
    ap.add_argument('--seller-rate', type=float, default=0); ap.add_argument('--seller-years', type=int, default=0); ap.add_argument('--seller-io-years', type=int, default=0)
    ap.add_argument('--minority-equity', type=float, default=0, help='equity from non-controlling investors (<20%, no control)')
    ap.add_argument('--equity-pct', type=float, default=0.10); ap.add_argument('--dscr-min', type=float, default=1.25)
    ap.add_argument('--term-years', type=int, default=10); ap.add_argument('--spread', type=float, default=None); ap.add_argument('--rate', type=float, default=None)
    ap.add_argument('--compare', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    base = dict(price=a.price, sde=a.sde, cash=a.cash, salary=a.salary, prime=a.prime, working_capital=a.working_capital,
                closing_costs=a.closing_costs, guaranty_fee=a.guaranty_fee, minority_equity=a.minority_equity, equity_pct=a.equity_pct,
                dscr_min=a.dscr_min, term_years=a.term_years, spread=a.spread, rate=a.rate)
    runs = []
    if a.compare:
        runs.append(structure(**base, label='A. Cash injection only, no seller note'))
        runs.append(structure(**base, seller_note=0.10 * a.price, seller_standby='full', seller_rate=a.seller_rate or 6.0, seller_years=10, label='B. 10% seller note, full standby (earns injection credit)'))
        runs.append(structure(**base, seller_note=0.20 * a.price, seller_standby='partial', seller_rate=a.seller_rate or 6.0, seller_years=7, seller_io_years=2, label='C. 20% seller note, 2y interest-only then 5y amortising (counts in DSCR)'))
    else:
        runs.append(structure(**base, seller_note=a.seller_note, seller_standby=a.seller_standby, seller_rate=a.seller_rate,
                              seller_years=a.seller_years, seller_io_years=a.seller_io_years, label='Your structure'))
    for r in runs:
        kw = dict(base); kw.update(seller_note=r['seller_note'], seller_standby=r['seller_standby'], seller_rate=a.seller_rate or 6.0,
                                  seller_years=(10 if r['seller_standby'] == 'full' else a.seller_years or 7), seller_io_years=a.seller_io_years)
        r['max_price_at_dscr_min'] = max_price_at_dscr(kw, a.dscr_min)
    if a.json:
        print(json.dumps(runs, indent=2, default=float))
    else:
        for r in runs:
            print(fmt(r)); print(f"Max price this structure supports at DSCR {a.dscr_min:.2f}: ${r['max_price_at_dscr_min']:,.0f}\n")
        print("Assumptions you passed in: prime, salary, fee, working capital, closing costs. Rules: SOP 50 10 8 / 8.1 — re-verify per references/sba-rules.md. Not lending, legal or tax advice.")

if __name__ == '__main__':
    main()
