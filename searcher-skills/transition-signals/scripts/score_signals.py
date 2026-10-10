#!/usr/bin/env python3
"""Combine registry facts, SBA/5500 facts and website signals into a ranked list
with three transition scores plus a 'boomer-coded web presence' score. Claude's
own read of the evidence goes in judgements.csv (see references/rubric.md) and
is merged when present.

Usage:
  python score_signals.py --survivors survivors.csv --site site_signals.csv [--judgements judgements.csv] --out ranked_targets.csv
"""
import argparse, re
import pandas as pd

def b(x):
    return str(x).strip().lower() in ('true', '1', 'yes')

def num(x, default=0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default

def registry_generation_signal(officers):
    """JR/SR/II/III in officer names, or two officers sharing a surname with different first names."""
    if not isinstance(officers, str) or not officers:
        return False, ''
    names = [i.split(':', 1)[-1].strip() for i in officers.split(';') if i.strip()]
    gen = [n for n in names if re.search(r'\b(JR|SR|II|III|IV)\b', n.upper())]
    surn = {}
    for n in names:
        s = n.split(',')[0].strip().upper() if ',' in n else n.split()[-1].upper()
        surn.setdefault(s, []).append(n)
    shared = [v for v in surn.values() if len(set(v)) > 1]
    ev = []
    if gen: ev.append('generational suffix: ' + '; '.join(gen))
    if shared: ev.append('shared surname: ' + '; '.join(shared[0]))
    return bool(gen or shared), ' | '.join(ev)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--survivors', required=True)
    ap.add_argument('--site', default=None)
    ap.add_argument('--judgements', default=None)
    ap.add_argument('--out', default='ranked_targets.csv')
    a = ap.parse_args()
    s = pd.read_csv(a.survivors, dtype=str, keep_default_na=False)
    site = pd.read_csv(a.site, dtype=str, keep_default_na=False) if a.site else pd.DataFrame(columns=['business_name'])
    df = s.merge(site.drop(columns=['website'], errors='ignore'), on='business_name', how='left')
    df = df.fillna('')

    rows = []
    for _, r in df.iterrows():
        yrs = num(r.get('years_registered'))
        hc = num(r.get('headcount_5500'), default=None)
        jobs = num(r.get('ppp_jobs'), default=None)
        officers = r.get('officers', '')
        n_off = int(num(r.get('officer_count')))
        gen_reg, gen_ev = registry_generation_signal(officers)
        has_site = r.get('fetch_status') == 'ok'

        # --- owner-operated: small, few officers, owner surname fronts the site
        oo = 0; oo_ev = []
        if n_off and n_off <= 2: oo += 30; oo_ev.append(f'{n_off} officer(s) on registry')
        if b(r.get('officer_surname_hit')): oo += 30; oo_ev.append('officer surname on website: ' + r.get('officer_surnames_on_site', ''))
        if num(r.get('owner_operated')): oo += 25; oo_ev.append(r.get('owner_operated_evidence', '')[:160])
        size = hc if hc is not None else jobs
        if size is not None and size <= 15: oo += 15; oo_ev.append(f'headcount ~{int(size)}')
        # --- named successor: generation words, son/daughter, registry family pattern
        sc = 0; sc_ev = []
        if gen_reg:
            sc += (40 if 'generational suffix' in gen_ev else 20); sc_ev.append(gen_ev)
        if num(r.get('generation')): sc += 30; sc_ev.append(r.get('generation_evidence', '')[:160])
        if num(r.get('son_daughter')): sc += 20; sc_ev.append(r.get('son_daughter_evidence', '')[:160])
        if num(r.get('succession_words')): sc += 20; sc_ev.append(r.get('succession_words_evidence', '')[:160])
        if b(r.get('family_surname_signal')) and not gen_reg: sc += 10; sc_ev.append('two officers share a surname')
        # --- retirement / transition language
        rt = 0; rt_ev = []
        if num(r.get('retire')): rt += 50; rt_ev.append(r.get('retire_evidence', '')[:160])
        if num(r.get('new_ownership')): rt += 30; rt_ev.append(r.get('new_ownership_evidence', '')[:160])
        if num(r.get('for_sale')): rt += 40; rt_ev.append(r.get('for_sale_evidence', '')[:160])
        if yrs >= 40: rt += 10; rt_ev.append(f'{int(yrs)} years registered')
        # --- boomer-coded web presence (higher = less modern)
        bc = 0; bc_ev = []
        if not has_site:
            bc = None
        else:
            if not b(r.get('ad_pixel')): bc += 25; bc_ev.append('no analytics/ad pixel')
            if not b(r.get('booking_widget')): bc += 20; bc_ev.append('no online booking')
            if not b(r.get('social_links')): bc += 15; bc_ev.append('no social links')
            if not b(r.get('has_viewport_meta')): bc += 20; bc_ev.append('not mobile-responsive')
            cy = r.get('copyright_year', '')
            if cy and cy.isdigit() and int(cy) <= pd.Timestamp.today().year - 3: bc += 20; bc_ev.append(f'copyright year {cy}')
            if not b(r.get('https')): bc += 10; bc_ev.append('no HTTPS')
            if not b(r.get('chat_widget')) and not b(r.get('reviews_widget')): bc += 5
        fy = r.get('founded_year_value', '')
        rows.append({
            'business_name': r['business_name'], 'city': r.get('city', ''), 'years_registered': int(yrs) if yrs else '',
            'founded_year_on_site': fy, 'headcount_5500': r.get('headcount_5500', ''), 'ppp_jobs': r.get('ppp_jobs', ''),
            'website': r.get('final_url', '') or r.get('website', ''), 'site_fetched': has_site,
            'owner_operated_score': min(oo, 100), 'owner_operated_evidence': ' | '.join(e for e in oo_ev if e),
            'named_successor_score': min(sc, 100), 'named_successor_evidence': ' | '.join(e for e in sc_ev if e),
            'retirement_signal_score': min(rt, 100), 'retirement_signal_evidence': ' | '.join(e for e in rt_ev if e),
            'boomer_coded_score': ('' if bc is None else min(bc, 100)), 'boomer_coded_evidence': ' | '.join(bc_ev),
            'officers': officers, 'registry_doc_number': r.get('registry_doc_number', ''),
        })
    out = pd.DataFrame(rows)
    # carry every other survivors column through so downstream skills have the full record
    extra = s[['business_name'] + [c for c in s.columns if c not in out.columns and c != 'business_name']].drop_duplicates('business_name')
    out = out.merge(extra, on='business_name', how='left')
    # Claude's judgements (probabilities 0-1) override the heuristic scores when present
    if a.judgements:
        j = pd.read_csv(a.judgements, dtype=str, keep_default_na=False)
        out = out.merge(j, on='business_name', how='left')
    def prio(r):
        oo = num(r.get('owner_operated_p'), None); sc = num(r.get('named_successor_p'), None); rt = num(r.get('retirement_p'), None)
        if oo is None: oo = r['owner_operated_score'] / 100
        if sc is None: sc = r['named_successor_score'] / 100
        if rt is None: rt = r['retirement_signal_score'] / 100
        bc = num(r.get('boomer_coded_score'), 50) / 100
        # ready to hand over = owner still central, no successor, retirement cues, old-school presence
        return round(100 * (0.35 * oo + 0.30 * (1 - sc) + 0.20 * rt + 0.15 * bc), 1)
    out['transition_priority'] = out.apply(prio, axis=1)
    out = out.sort_values(['transition_priority', 'years_registered'], ascending=[False, False])
    out.to_csv(a.out, index=False)
    print(f'{len(out)} targets ranked -> {a.out}')
    print(out[['business_name', 'years_registered', 'transition_priority', 'owner_operated_score', 'named_successor_score', 'retirement_signal_score', 'boomer_coded_score']].head(15).to_string(index=False))

if __name__ == '__main__':
    main()
