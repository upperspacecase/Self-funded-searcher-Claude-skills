#!/usr/bin/env python3
"""Download SBA PPP FOIA and SBA 7(a) FOIA loan files and filter to one state + NAICS prefix.

Keyless. Discovers the current file URLs through data.sba.gov's CKAN API, so the
script keeps working when SBA refreshes the files and the filenames change.

Usage:
  python fetch_sba.py --state FL --naics 238220 --min-loan 150000 --outdir data
Outputs:
  data/sba_ppp_<STATE>_<naics>.csv   (one row per PPP loan)
  data/sba_7a_<STATE>_<naics>.csv    (one row per 7(a) loan, 1991-present)
"""
import argparse, os, sys, re
import requests
import pandas as pd
from common import require_cols

CKAN = "https://data.sba.gov/api/3/action/package_show?id={}"
DATASETS = {'ppp': 'ppp-foia', '7a': '7-a-504-foia'}

PPP_SPEC = {
    'loan_number': ['LoanNumber'],
    'date_approved': ['DateApproved'],
    'name': ['BorrowerName'],
    'address': ['BorrowerAddress'],
    'city': ['BorrowerCity'],
    'state': ['BorrowerState'],
    'zip': ['BorrowerZip'],
    'naics': ['NAICSCode'],
    'amount': ['CurrentApprovalAmount', 'InitialApprovalAmount'],
    'forgiven': ['ForgivenessAmount'],
    'jobs': ['JobsReported'],
    'business_type': ['BusinessType'],
}
SEVENA_SPEC = {
    'name': ['BorrName'],
    'address': ['BorrStreet'],
    'city': ['BorrCity'],
    'state': ['BorrState'],
    'zip': ['BorrZip'],
    'naics': ['NaicsCode'],
    'amount': ['GrossApproval'],
    'date_approved': ['ApprovalDate'],
    'jobs': ['JobsSupported'],
    'business_age': ['BusinessAge'],
    'loan_status': ['LoanStatus'],
    'term_months': ['TermInMonths'],
}

def resources(dataset):
    r = requests.get(CKAN.format(dataset), timeout=60)
    r.raise_for_status()
    res = r.json()['result']['resources']
    return [(x.get('name') or x.get('url', '').split('/')[-1], x['url']) for x in res if x.get('url')]

def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        tmp = dest + '.part'
        with open(tmp, 'wb') as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        os.replace(tmp, dest)
    return dest

def filter_file(path, spec, state, naics_prefixes, min_amount, source):
    keep = []
    first = True
    colmap = None
    for chunk in pd.read_csv(path, dtype=str, chunksize=200_000, low_memory=False, on_bad_lines='skip', encoding_errors='replace'):
        if first:
            colmap = require_cols(chunk, {k: v for k, v in spec.items() if k in ('name','state','naics','amount')}, source)
            # optional columns
            for k, v in spec.items():
                if k not in colmap:
                    from common import pick_col
                    c = pick_col(chunk, v)
                    if c: colmap[k] = c
            first = False
        st = chunk[colmap['state']].astype(str).str.strip().str.upper()
        nc = chunk[colmap['naics']].astype(str).str.strip()
        amt = pd.to_numeric(chunk[colmap['amount']], errors='coerce')
        mask = (st == state) & nc.str.startswith(tuple(naics_prefixes)) & (amt >= min_amount)
        sub = chunk[mask]
        if len(sub):
            out = pd.DataFrame({k: sub[c] for k, c in colmap.items()})
            out['source'] = source
            out['source_file'] = os.path.basename(path)
            keep.append(out)
    if not keep:
        return pd.DataFrame(columns=list(spec.keys()) + ['source', 'source_file'])
    return pd.concat(keep, ignore_index=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--naics', required=True, help='comma-separated prefixes, e.g. 238220 or 2382')
    ap.add_argument('--min-loan', type=float, default=0)
    ap.add_argument('--outdir', default='data')
    ap.add_argument('--skip-ppp', action='store_true')
    ap.add_argument('--skip-7a', action='store_true')
    ap.add_argument('--ppp-small', action='store_true', help='also pull the under-$150k PPP files (12 large files)')
    a = ap.parse_args()
    state = a.state.upper()
    prefixes = [p.strip() for p in a.naics.split(',') if p.strip()]
    raw = os.path.join(a.outdir, 'raw'); os.makedirs(raw, exist_ok=True)

    if not a.skip_ppp:
        files = resources(DATASETS['ppp'])
        wanted = [(n, u) for n, u in files if re.search(r'public_150k_plus.*\.csv$', n, re.I)]
        if a.ppp_small:
            wanted += [(n, u) for n, u in files if re.search(r'public_up_to_150k.*\.csv$', n, re.I)]
        if not wanted:
            print('PPP: no CSV resources found in CKAN listing; names seen:', [n for n, _ in files][:20])
        parts = []
        for n, u in wanted:
            p = download(u, os.path.join(raw, n))
            print('PPP file', n, '->', os.path.getsize(p) // (1 << 20), 'MB')
            parts.append(filter_file(p, PPP_SPEC, state, prefixes, a.min_loan, 'ppp'))
        ppp = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        out = os.path.join(a.outdir, f'sba_ppp_{state}_{"-".join(prefixes)}.csv')
        ppp.to_csv(out, index=False); print('PPP rows kept:', len(ppp), '->', out)

    if not a.skip_7a:
        files = resources(DATASETS['7a'])
        wanted = [(n, u) for n, u in files if re.search(r'7a', n, re.I) and n.lower().endswith('.csv')]
        if not wanted:
            print('7(a): no CSV resources found; names seen:', [n for n, _ in files][:30])
        parts = []
        for n, u in wanted:
            p = download(u, os.path.join(raw, n))
            print('7(a) file', n, '->', os.path.getsize(p) // (1 << 20), 'MB')
            parts.append(filter_file(p, SEVENA_SPEC, state, prefixes, a.min_loan, '7a'))
        sev = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        out = os.path.join(a.outdir, f'sba_7a_{state}_{"-".join(prefixes)}.csv')
        sev.to_csv(out, index=False); print('7(a) rows kept:', len(sev), '->', out)

if __name__ == '__main__':
    main()
