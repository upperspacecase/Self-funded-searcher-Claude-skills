#!/usr/bin/env python3
"""Join SBA loan files, the state registry, and Form 5500 into survivors.csv —
long-lived businesses in one industry, with the evidence behind each row.

Two modes:
  sba-first      start from SBA borrowers (they carry NAICS), find each in the
                 registry for charter date, FEI and officers, then Form 5500 for
                 headcount. High precision; misses businesses that never borrowed.
  registry-first start from every active registry entity old enough, keep the
                 ones whose name or Form 5500 business code points at the
                 industry, then attach any SBA history. High recall; noisier.

Usage:
  python build_survivors.py --state FL --naics 238220 --min-years 30 --mode sba-first --datadir data
"""
import argparse, os, re, sys
from datetime import date
import pandas as pd
from common import fuzzy_join, normalize_name, ein_key, zip5

KEYWORDS = {  # registry-first name filter per NAICS prefix; extend freely
    '238220': r'PLUMB|HVAC|AIR COND|A/C|HEATING|COOLING|MECHANICAL|REFRIGERATION',
    '238210': r'ELECTRIC',
    '238160': r'ROOF',
    '561730': r'LANDSCAP|LAWN|TREE|IRRIGATION',
    '561720': r'JANITOR|CLEANING|MAINTENANCE',
    '561710': r'PEST|TERMITE|EXTERMINAT',
    '8111': r'AUTO|AUTOMOTIVE|COLLISION|BODY SHOP|TRANSMISSION|TIRE|MUFFLER',
    '812320': r'CLEANERS|LAUNDRY|DRY CLEAN',
    '812310': r'LAUNDR|COIN',
    '812210': r'FUNERAL|MORTUARY|CREMAT',
    '541940': r'VETERINAR|ANIMAL HOSPITAL|ANIMAL CLINIC',
    '524210': r'INSURANCE',
    '484110': r'TRUCKING|TRANSPORT|FREIGHT|HAULING',
    '332710': r'MACHINE|MACHINING|TOOL',
}

def surname(n):
    if not isinstance(n, str) or not n.strip():
        return ''
    return n.split(',')[0].strip().upper() if ',' in n else n.strip().split()[-1].upper()

def officer_summary(row):
    items, surnames = [], []
    for i in range(1, 7):
        nm = row.get(f'off{i}_name', '')
        if isinstance(nm, str) and nm.strip():
            items.append(f"{row.get(f'off{i}_title', '').strip()}:{nm.strip()}")
            surnames.append(surname(nm))
    shared = len(surnames) - len(set(surnames)) if surnames else 0
    return '; '.join(items), len(items), shared > 0

def years_since(iso):
    if not isinstance(iso, str) or len(iso) < 10:
        return None
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return None
    today = date.today()
    return today.year - d.year - ((today.month, today.day) < (d.month, d.day))

def load_sba(datadir, state, naics):
    frames = []
    for kind in ('ppp', '7a'):
        p = os.path.join(datadir, f'sba_{kind}_{state}_{naics}.csv')
        if os.path.exists(p):
            df = pd.read_csv(p, dtype=str)
            if len(df):
                df['kind'] = kind
                frames.append(df)
    if not frames:
        return pd.DataFrame()
    sba = pd.concat(frames, ignore_index=True)
    sba['amount_num'] = pd.to_numeric(sba['amount'], errors='coerce')
    sba['year'] = pd.to_datetime(sba['date_approved'], errors='coerce').dt.year
    sba['_k'] = sba['name'].map(normalize_name) + '|' + sba['zip'].map(zip5)
    # one row per borrower with loan history rolled up
    g = sba.groupby('_k')
    agg = g.agg(name=('name', 'first'), address=('address', 'first'), city=('city', 'first'), state=('state', 'first'),
                zip=('zip', 'first'), naics=('naics', 'first'), sba_loan_count=('amount_num', 'size'),
                sba_max_loan=('amount_num', 'max'), sba_first_loan_year=('year', 'min'), sba_last_loan_year=('year', 'max'),
                kinds=('kind', lambda s: ','.join(sorted(set(s))))).reset_index(drop=True)
    ppp = sba[sba['kind'] == 'ppp'].copy()
    if len(ppp):
        ppp['forgiven_num'] = pd.to_numeric(ppp.get('forgiven'), errors='coerce')
        ppp['jobs_num'] = pd.to_numeric(ppp.get('jobs'), errors='coerce')
        pg = ppp.groupby('_k').agg(ppp_max_loan=('amount_num', 'max'), ppp_forgiven=('forgiven_num', 'max'),
                                   ppp_jobs=('jobs_num', 'max'), ppp_business_type=('business_type', 'first')).reset_index()
        pg['ppp_est_annual_payroll'] = (pg['ppp_max_loan'] / 2.5 * 12).round(0)
        pg['ppp_not_fully_forgiven'] = (pg['ppp_forgiven'].fillna(0) < pg['ppp_max_loan'] * 0.98)
        agg['_k'] = agg['name'].map(normalize_name) + '|' + agg['zip'].map(zip5)
        agg = agg.merge(pg, on='_k', how='left').drop(columns='_k')
    sev = sba[sba['kind'] == '7a']
    if len(sev) and 'business_age' in sev.columns:
        sg = sev.groupby('_k').agg(sba7a_business_age=('business_age', 'first'), sba7a_status=('loan_status', 'last')).reset_index()
        agg['_k'] = agg['name'].map(normalize_name) + '|' + agg['zip'].map(zip5)
        agg = agg.merge(sg, on='_k', how='left').drop(columns='_k')
    return agg

def attach_5500(df, f5500, name_col, city_col, zip_col, fei_col):
    if f5500 is None or not len(f5500):
        df['headcount_5500'] = pd.NA; df['headcount_source'] = ''; df['naics_5500'] = ''
        return df
    f = f5500.copy()
    f['ein_key'] = f['ein'].map(ein_key) if 'ein_key' not in f else f['ein_key'].fillna('')
    df['_ein'] = df[fei_col].map(ein_key) if fei_col in df else ''
    by_ein = f[f['ein_key'] != ''].drop_duplicates('ein_key').set_index('ein_key')
    hc, src, nc, py = [], [], [], []
    need_fuzzy = []
    for i, r in df.iterrows():
        e = r['_ein']
        if e and e in by_ein.index:
            m = by_ein.loc[e]
            hc.append(m.get('active_participants') if pd.notna(m.get('active_participants')) else m.get('participants_boy'))
            src.append('5500 via EIN'); nc.append(m.get('business_code', '')); py.append(m.get('form_year', ''))
        else:
            hc.append(pd.NA); src.append(''); nc.append(''); py.append(''); need_fuzzy.append(i)
    df['headcount_5500'] = hc; df['headcount_source'] = src; df['naics_5500'] = nc; df['f5500_year'] = py
    if need_fuzzy:
        sub = df.loc[need_fuzzy]
        j = fuzzy_join(sub, f, left_name=name_col, right_name='name', left_city=city_col, right_city='city',
                       left_zip=zip_col, right_zip='zip', threshold=92, right_prefix='f_')
        j.index = sub.index
        ok = j['match_block'] != 'none'
        for i in j.index[ok]:
            m = j.loc[i]
            val = m.get('f_active_participants')
            df.at[i, 'headcount_5500'] = val if pd.notna(val) else m.get('f_participants_boy')
            df.at[i, 'headcount_source'] = f"5500 via name ({int(m['match_score'])})"
            df.at[i, 'naics_5500'] = m.get('f_business_code', '')
            df.at[i, 'f5500_year'] = m.get('f_form_year', '')
    return df.drop(columns=['_ein'], errors='ignore')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--naics', required=True)
    ap.add_argument('--min-years', type=int, default=30)
    ap.add_argument('--mode', choices=['sba-first', 'registry-first'], default='sba-first')
    ap.add_argument('--datadir', default='data')
    ap.add_argument('--threshold', type=int, default=88, help='fuzzy match acceptance score 0-100')
    ap.add_argument('--keywords', help='regex for registry-first name filter (overrides built-in)')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    state = a.state.upper()
    out = a.out or os.path.join(a.datadir, f'survivors_{state}_{a.naics}_{a.min_years}y.csv')

    reg_path = os.path.join(a.datadir, 'sunbiz_active.csv' if state == 'FL' else f'registry_{state}_active.csv')
    if not os.path.exists(reg_path):
        sys.exit(f'registry file missing: {reg_path}. Run the registry fetch first.')
    reg = pd.read_csv(reg_path, dtype=str, keep_default_na=False)
    reg['years_registered'] = reg['file_date_iso'].map(years_since)
    f5500_path = os.path.join(a.datadir, f'f5500_{state}.csv')
    f5500 = pd.read_csv(f5500_path, dtype=str, keep_default_na=False) if os.path.exists(f5500_path) else None
    if f5500 is not None:
        for c in ('participants_boy', 'active_participants'):
            f5500[c] = pd.to_numeric(f5500[c], errors='coerce')

    sba = load_sba(a.datadir, state, a.naics)

    if a.mode == 'sba-first':
        if not len(sba):
            sys.exit('no SBA rows for this state/NAICS; run fetch_sba.py or use --mode registry-first')
        j = fuzzy_join(sba, reg, left_name='name', right_name='cor_name', left_city='city', right_city='city',
                       left_zip='zip', right_zip='zip', threshold=a.threshold, right_prefix='reg_')
        j['charter_date'] = j.get('reg_file_date_iso', '')
        j['years_registered'] = j['charter_date'].map(years_since)
        j['business_name'] = j['reg_cor_name'].where(j['match_block'] != 'none', j['name'])
        base = j
        name_col, fei_col = 'business_name', 'reg_fei'
        off_prefix = 'reg_'
        un = j[j['match_block'] == 'none'][['name', 'city', 'zip', 'naics', 'sba_max_loan', 'match_score']]
        un_path = out.replace('.csv', '_unmatched_sba.csv')
        un.to_csv(un_path, index=False)
        print(f'SBA borrowers with no registry match: {len(un):,} -> {un_path} (recall check: raise --threshold tolerance or inspect names)')
    else:
        kw = a.keywords or next((v for k, v in KEYWORDS.items() if a.naics.startswith(k)), None)
        old = reg[reg['years_registered'].fillna(-1) >= a.min_years].copy()
        old['_hit_kw'] = old['cor_name'].str.contains(kw, case=False, regex=True, na=False) if kw else False
        # Form 5500 business code says this employer is in the industry (cheap EIN lookup)
        old['_ein'] = old['fei'].map(ein_key)
        if f5500 is not None and len(f5500):
            code_by_ein = f5500[f5500['ein_key'].astype(str) != ''].set_index('ein_key')['business_code'].astype(str)
            old['_hit_5500'] = old['_ein'].map(code_by_ein).fillna('').str.startswith(a.naics)
        else:
            old['_hit_5500'] = False
        # SBA borrower in the industry that matches a registry entity (fuzzy from the small side)
        old['_hit_sba'] = False
        if len(sba):
            sj = fuzzy_join(sba, old, left_name='name', right_name='cor_name', left_city='city', right_city='city',
                            left_zip='zip', right_zip='zip', threshold=a.threshold, right_prefix='reg_')
            hit_docs = set(sj.loc[sj['match_block'] != 'none', 'reg_cor_number'])
            old['_hit_sba'] = old['cor_number'].isin(hit_docs)
        old['industry_evidence'] = old.apply(lambda r: ','.join(k for k, v in (('name', r['_hit_kw']), ('5500', r['_hit_5500']), ('sba', r['_hit_sba'])) if v), axis=1)
        old = old[old['_hit_kw'] | old['_hit_5500'] | old['_hit_sba']].copy()
        old = old.rename(columns={'cor_name': 'business_name', 'file_date_iso': 'charter_date'})
        if len(sba) and len(old):
            j = fuzzy_join(old, sba, left_name='business_name', right_name='name', left_city='city', right_city='city',
                           left_zip='zip', right_zip='zip', threshold=a.threshold, right_prefix='sba_')
            for c in ('sba_loan_count', 'sba_max_loan', 'sba_first_loan_year', 'sba_last_loan_year', 'naics', 'kinds',
                      'ppp_est_annual_payroll', 'ppp_not_fully_forgiven', 'ppp_jobs', 'sba7a_business_age'):
                src = 'sba_' + c
                if src in j.columns: j[c] = j[src]
            base = j
        else:
            base = old
            base['match_block'] = 'none'; base['match_score'] = 0
        name_col, fei_col = 'business_name', 'fei'
        off_prefix = ''

    base = base[base['years_registered'].fillna(-1) >= a.min_years].copy() if a.mode == 'sba-first' else base
    # officers
    offs = base.apply(lambda r: officer_summary({k.replace(off_prefix, '', 1) if off_prefix else k: v for k, v in r.items()}), axis=1)
    base['officers'] = [o[0] for o in offs]; base['officer_count'] = [o[1] for o in offs]; base['family_surname_signal'] = [o[2] for o in offs]
    city_col = 'city'; zip_col = 'zip'
    base = attach_5500(base, f5500, name_col, city_col, zip_col, fei_col)

    def evidence(r):
        bits = []
        if a.mode == 'sba-first':
            bits.append(f"registry match {r['match_score']} via {r['match_block']}" if r.get('match_block', 'none') != 'none' else 'NO registry match')
        else:
            bits.append(f"industry via {r.get('industry_evidence', '')}")
            if r.get('match_block', 'none') != 'none':
                bits.append(f"SBA match {r['match_score']} via {r['match_block']}")
        if pd.notna(r.get('sba_loan_count')) and r.get('sba_loan_count'):
            bits.append(f"SBA loans: {int(r['sba_loan_count'])} ({r.get('kinds', '')})")
        if r.get('headcount_source'):
            bits.append(r['headcount_source'])
        return '; '.join(bits)
    base['match_evidence'] = base.apply(evidence, axis=1)

    cols = ['business_name', 'city', 'state', 'zip', 'charter_date', 'years_registered',
            f'{off_prefix}filing_type', f'{off_prefix}cor_number', f'{off_prefix}report_year1',
            'naics', 'naics_5500', 'sba_loan_count', 'sba_first_loan_year', 'sba_last_loan_year', 'sba_max_loan',
            'ppp_est_annual_payroll', 'ppp_jobs', 'ppp_not_fully_forgiven', 'sba7a_business_age',
            'headcount_5500', 'headcount_source', 'f5500_year', 'officers', 'officer_count', 'family_surname_signal',
            'industry_evidence', 'match_score', 'match_block', 'match_evidence']
    cols = [c for c in cols if c in base.columns]
    res = base[cols].rename(columns={f'{off_prefix}filing_type': 'filing_type', f'{off_prefix}cor_number': 'registry_doc_number',
                                     f'{off_prefix}report_year1': 'last_annual_report_year'})
    res = res.sort_values(['years_registered', 'sba_max_loan'], ascending=[False, False])
    res.to_csv(out, index=False)
    matched = (res['match_block'] != 'none').sum() if 'match_block' in res else len(res)
    print(f'mode={a.mode} | rows out: {len(res):,} | with registry match: {matched:,} | 5500 headcount: {res["headcount_5500"].notna().sum():,}')
    print('->', out)

if __name__ == '__main__':
    main()
