#!/usr/bin/env python3
"""Assemble a one-page first-call brief from ranked_targets.csv (or survivors.csv).

Usage:
  python build_brief.py --targets ranked_targets.csv --name "Advent Air" --out brief_advent.md
"""
import argparse, os, sys
from datetime import date
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

def money(x):
    try:
        return f"${float(x):,.0f}"
    except (TypeError, ValueError):
        return 'n/a'

def pick(df, name):
    m = df[df['business_name'].str.contains(name, case=False, regex=False)]
    if len(m) == 0:
        sys.exit(f'No business matching "{name}". Names available start with: {df["business_name"].head(10).tolist()}')
    if len(m) > 1:
        print('Several matches; using the first:', m['business_name'].tolist())
    return m.iloc[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--targets', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    df = pd.read_csv(a.targets, dtype=str, keep_default_na=False)
    r = pick(df, a.name).to_dict()
    g = lambda k, d='n/a': (r.get(k) or d)
    tmpl = open(os.path.join(HERE, '..', 'assets', 'brief-template.md')).read()

    yrs = g('years_registered', '?')
    hc = g('headcount_5500', '')
    size = f"about {hc} people on the benefit plan" if hc else (f"{g('ppp_jobs')} jobs reported on the 2020 PPP application" if g('ppp_jobs', '') else "headcount not in public records")
    summary = (f"{g('business_name')} has been registered in {g('city', 'its city')} since {g('charter_date', '?')} — {yrs} years. "
               f"Officers on file: {g('officers', 'none listed')}. Size: {size}. "
               f"SBA history: {g('sba_loan_count', '0')} loan(s). "
               + (f"The website claims a founding year of {g('founded_year_on_site')}. " if g('founded_year_on_site', '') else ''))
    unknowns = []
    if not hc: unknowns.append('- True headcount (no Form 5500 on file — may have no benefit plan)')
    if not g('website', ''): unknowns.append('- Whether they have a website at all')
    unknowns += ['- Revenue and SDE — nothing public carries this', '- Whether the owner is actually a seller, or just old enough to be asked',
                 '- Lease terms and whether the premises are owned', '- Whose name the trade licence is in']
    opening = (f"\"I'm not a broker. I'm one person looking to buy one good {g('city', 'local')} business and run it myself. "
               f"You've been at this since {g('founded_year_on_site') or g('charter_date', '?')[:4]} and that's rare. "
               f"Would you be open to a coffee — no agenda beyond hearing how you built it?\"")
    qb = open(os.path.join(HERE, '..', 'references', 'question-bank.md')).read()
    questions = '\n'.join(l for l in qb.splitlines() if l.startswith('- ') and l.rstrip().endswith('?'))
    listen = ('- Passive vs active: "thought about it" vs "talked to a broker"\n- Who they name when asked what breaks if they leave\n'
              '- Whether price, speed, or people comes first when they describe a good outcome')
    red = []
    if str(g('ppp_not_fully_forgiven', '')).lower() == 'true': red.append('- PPP loan not fully forgiven — ask what happened in 2020–21')
    if str(g('family_surname_signal', '')).lower() == 'true' or int(float(g('named_successor_score', '0') or 0)) >= 40:
        red.append('- Family on the registry or on the site — is there an heir, and do they want it?')
    if int(float(g('owner_operated_score', '0') or 0)) >= 70: red.append('- Owner is the business — plan for a long transition and price the key-person risk')
    if not red: red.append('- None visible in public records; the call will surface them')
    out = tmpl.format(today=date.today().isoformat(), business_name=g('business_name'), city=g('city'), charter_date=g('charter_date'),
                      years_registered=yrs, registry_doc_number=g('registry_doc_number'), filing_type=g('filing_type'),
                      founded_year_on_site=g('founded_year_on_site'), officers=g('officers'), headcount_5500=g('headcount_5500'),
                      ppp_jobs=g('ppp_jobs'), ppp_est_annual_payroll=money(g('ppp_est_annual_payroll', '')), sba_loan_count=g('sba_loan_count', '0'),
                      sba_last_loan_year=str(g('sba_last_loan_year')).replace('.0', ''), sba_max_loan=money(g('sba_max_loan', '')), website=g('website'),
                      owner_operated_score=g('owner_operated_score', '—'), owner_operated_evidence=g('owner_operated_evidence', ''),
                      named_successor_score=g('named_successor_score', '—'), named_successor_evidence=g('named_successor_evidence', ''),
                      retirement_signal_score=g('retirement_signal_score', '—'), retirement_signal_evidence=g('retirement_signal_evidence', ''),
                      boomer_coded_score=g('boomer_coded_score', '—'), boomer_coded_evidence=g('boomer_coded_evidence', ''),
                      summary_paragraph=summary, unknowns='\n'.join(unknowns), opening_line=opening, questions=questions, listen_for=listen, red_flags='\n'.join(red))
    path = a.out or f"brief_{g('business_name').split()[0].lower()}.md"
    open(path, 'w').write(out)
    print('->', path)

if __name__ == '__main__':
    main()
