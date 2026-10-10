#!/usr/bin/env python3
"""Download DOL Form 5500 and 5500-SF 'Latest' datasets for recent years and
filter to one state. Yields headcount (plan participants) and a NAICS business
code per sponsoring employer, keyed by EIN.

Keyless. Discovers zip links from the DOL datasets page; falls back to the
known URL pattern if the page layout changes.

Usage:
  python fetch_5500.py --state FL --years 2024,2023 --outdir data
Output:
  data/f5500_<STATE>.csv
"""
import argparse, os, re, io, zipfile, sys
import requests
import pandas as pd
from common import ein_key

PAGE = "https://www.dol.gov/agencies/ebsa/about-ebsa/our-activities/public-disclosure/foia/form-5500-datasets"
FALLBACK = {
    'sf': "https://askebsa.dol.gov/FOIA%20Files/{y}/Latest/F_5500_SF_{y}_Latest.zip",
    'full': "https://askebsa.dol.gov/FOIA%20Files/{y}/Latest/F_5500_{y}_Latest.zip",
}
# Column patterns (regex, case-insensitive) tried in order.
PATTERNS = {
    'name': [r'^SF_SPONSOR_NAME$', r'^SPONSOR_DFE_NAME$', r'SPONS.*NAME'],
    'ein': [r'^SF_SPONS_EIN$', r'^SPONS_DFE_EIN$', r'SPONS.*EIN'],
    'city': [r'^SF_SPONS_US_CITY$', r'^SPONS_DFE_MAIL_US_CITY$', r'SPONS.*US_CITY'],
    'state': [r'^SF_SPONS_US_STATE$', r'^SPONS_DFE_MAIL_US_STATE$', r'SPONS.*US_STATE'],
    'zip': [r'^SF_SPONS_US_ZIP$', r'^SPONS_DFE_MAIL_US_ZIP$', r'SPONS.*US_ZIP'],
    'participants_boy': [r'^SF_TOT_PARTCP_BOY_CNT$', r'^TOT_PARTCP_BOY_CNT$', r'TOT_PARTCP_BOY'],
    'active_participants': [r'^SF_TOT_ACT_PARTCP_CNT$', r'^TOT_ACTIVE_PARTCP_CNT$', r'ACT.*PARTCP'],
    'plan_year_begin': [r'^SF_PLAN_YEAR_BEGIN_DATE$', r'^FORM_PLAN_YEAR_BEGIN_DATE$', r'PLAN_YEAR_BEGIN'],
    'business_code': [r'^SF_BUSINESS_CODE$', r'^BUSINESS_CODE$', r'BUSINESS_CODE'],
    'plan_name': [r'^SF_PLAN_NAME$', r'^PLAN_NAME$', r'PLAN_NAME'],
}

def find_col(cols, pats):
    for p in pats:
        for c in cols:
            if re.search(p, c, re.I):
                return c
    return None

def discover(years):
    links = {}
    try:
        html = requests.get(PAGE, timeout=60).text
        hrefs = re.findall(r'href="([^"]+\.zip)"', html, re.I)
        for h in hrefs:
            for y in years:
                if f'5500_SF_{y}' in h and 'Latest' in h:
                    links[('sf', y)] = h if h.startswith('http') else 'https://www.dol.gov' + h
                elif f'5500_{y}' in h and 'Latest' in h and '_SF_' not in h:
                    links[('full', y)] = h if h.startswith('http') else 'https://www.dol.gov' + h
    except requests.RequestException as e:
        print('datasets page unreachable, using fallback URLs:', e)
    for y in years:
        for kind in ('sf', 'full'):
            links.setdefault((kind, y), FALLBACK[kind].format(y=y))
    return links

def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    with requests.get(url, stream=True, timeout=900) as r:
        r.raise_for_status()
        tmp = dest + '.part'
        with open(tmp, 'wb') as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        os.replace(tmp, dest)
    return dest

def extract_rows(zip_path, state, kind, year):
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith('.csv')]
        for m in members:
            with zf.open(m) as fh:
                for chunk in pd.read_csv(io.TextIOWrapper(fh, encoding='latin-1', errors='replace'), dtype=str, chunksize=200_000, low_memory=False, on_bad_lines='skip'):
                    cols = list(chunk.columns)
                    cm = {k: find_col(cols, v) for k, v in PATTERNS.items()}
                    if not cm['name'] or not cm['state']:
                        print('  unrecognised layout in', m, '; first columns:', cols[:15]); break
                    sub = chunk[chunk[cm['state']].astype(str).str.strip().str.upper() == state]
                    if len(sub):
                        rec = pd.DataFrame({k: (sub[c] if c else '') for k, c in cm.items()})
                        rec['form'] = kind; rec['form_year'] = year
                        out.append(rec)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=list(PATTERNS) + ['form', 'form_year'])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--years', default='2024,2023')
    ap.add_argument('--outdir', default='data')
    ap.add_argument('--sf-only', action='store_true', help='skip the full Form 5500 (large plans, 100+ participants)')
    a = ap.parse_args()
    state = a.state.upper()
    years = [int(y) for y in a.years.split(',')]
    raw = os.path.join(a.outdir, 'raw'); os.makedirs(raw, exist_ok=True)
    links = discover(years)
    parts = []
    for (kind, y), url in sorted(links.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        if a.sf_only and kind == 'full':
            continue
        dest = os.path.join(raw, f'F_5500_{"SF_" if kind == "sf" else ""}{y}_Latest.zip')
        try:
            download(url, dest)
        except requests.HTTPError as e:
            print('skip', url, e); continue
        print('reading', dest)
        parts.append(extract_rows(dest, state, kind, y))
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(df):
        df['ein_key'] = df['ein'].map(ein_key)
        for c in ('participants_boy', 'active_participants'):
            df[c] = pd.to_numeric(df[c], errors='coerce')
        # keep the most recent filing per EIN
        df = df.sort_values(['ein_key', 'form_year'], ascending=[True, False]).drop_duplicates('ein_key', keep='first')
    out = os.path.join(a.outdir, f'f5500_{state}.csv')
    df.to_csv(out, index=False)
    print(f'{len(df):,} sponsoring employers in {state} -> {out}')

if __name__ == '__main__':
    main()
