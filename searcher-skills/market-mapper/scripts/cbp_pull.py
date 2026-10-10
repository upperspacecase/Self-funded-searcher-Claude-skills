#!/usr/bin/env python3
"""Pull County Business Patterns establishment counts by county and size band.

Keyless. The Census API permits a modest number of calls per day without a key;
this script makes one or two.

Usage:
  python cbp_pull.py --state FL --naics 238220 --out market.csv
"""
import argparse
import sys
import json
import requests
import pandas as pd

STATE_FIPS = {
 'AL':'01','AK':'02','AZ':'04','AR':'05','CA':'06','CO':'08','CT':'09','DE':'10','DC':'11','FL':'12','GA':'13',
 'HI':'15','ID':'16','IL':'17','IN':'18','IA':'19','KS':'20','KY':'21','LA':'22','ME':'23','MD':'24','MA':'25',
 'MI':'26','MN':'27','MS':'28','MO':'29','MT':'30','NE':'31','NV':'32','NH':'33','NJ':'34','NM':'35','NY':'36',
 'NC':'37','ND':'38','OH':'39','OK':'40','OR':'41','PA':'42','RI':'44','SC':'45','SD':'46','TN':'47','TX':'48',
 'UT':'49','VT':'50','VA':'51','WA':'53','WV':'54','WI':'55','WY':'56'}

# Employment-size codes used by CBP (EMPSZES).
SIZE_BANDS = {
 '001': 'all', '212': 'lt5', '220': '5to9', '230': '10to19', '241': '20to49',
 '242': '50to99', '251': '100to249', '252': '250to499', '254': '500to999', '260': '1000plus'}

def fetch(year, naics_var, state_fips, naics):
    url = f"https://api.census.gov/data/{year}/cbp"
    params = {
        'get': 'NAME,ESTAB,EMPSZES',
        'for': 'county:*',
        'in': f'state:{state_fips}',
        naics_var: naics,
    }
    r = requests.get(url, params=params, timeout=60)
    if r.status_code != 200:
        return None, f"{year}/{naics_var}: HTTP {r.status_code} {r.text[:120]}"
    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, f"{year}/{naics_var}: non-JSON response"
    if not data or len(data) < 2:
        return None, f"{year}/{naics_var}: empty"
    return pd.DataFrame(data[1:], columns=data[0]), None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--naics', required=True)
    ap.add_argument('--out', default='market.csv')
    ap.add_argument('--year', type=int, default=None, help='force a CBP vintage')
    a = ap.parse_args()
    fips = STATE_FIPS.get(a.state.upper())
    if not fips:
        sys.exit(f"Unknown state {a.state}")
    years = [a.year] if a.year else [2023, 2022]
    df, errors = None, []
    for y in years:
        for var in ('NAICS2022', 'NAICS2017'):
            df, err = fetch(y, var, fips, a.naics)
            if df is not None:
                used = (y, var); break
            errors.append(err)
        if df is not None:
            break
    if df is None:
        sys.exit("Census API returned nothing. Tried: " + '; '.join(errors))
    df['ESTAB'] = pd.to_numeric(df['ESTAB'], errors='coerce')
    df['band'] = df['EMPSZES'].map(SIZE_BANDS).fillna(df['EMPSZES'])
    pivot = df.pivot_table(index='NAME', columns='band', values='ESTAB', aggfunc='sum').reset_index()
    for b in ['all','lt5','5to9','10to19','20to49','50to99','100to249','250to499','500to999','1000plus']:
        if b not in pivot.columns:
            pivot[b] = pd.NA
    pivot = pivot.rename(columns={'NAME': 'county'})
    small = pivot[['lt5','5to9','10to19']].sum(axis=1, min_count=1)
    pivot['under20_share'] = (small / pivot['all']).round(3)
    pivot = pivot.sort_values('all', ascending=False)
    total = pivot['all'].sum()
    pivot['share_of_state'] = (pivot['all'] / total).round(3) if total else pd.NA
    cols = ['county','all','share_of_state','under20_share','lt5','5to9','10to19','20to49','50to99','100to249','250to499','500to999','1000plus']
    pivot[cols].to_csv(a.out, index=False)
    state_under20 = (pivot[['lt5','5to9','10to19']].sum().sum() / total) if total else float('nan')
    print(f"vintage {used[0]} via {used[1]} | {a.state.upper()} NAICS {a.naics}")
    print(f"state establishments: {int(total)} | under-20-employee share: {state_under20:.0%}")
    print(pivot[cols].head(10).to_string(index=False))
    print(f"wrote {a.out}")

if __name__ == '__main__':
    main()
