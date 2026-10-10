"""Shared helpers: column aliasing, name normalisation, blocked fuzzy matching.

Every government file spells things its own way. This module makes them comparable
without pretending the match is exact — every match carries a score.
"""
import re
import pandas as pd

# Corporate suffixes and noise words stripped before matching.
SUFFIXES = {
    'INC', 'INCORPORATED', 'LLC', 'L L C', 'LC', 'CORP', 'CORPORATION', 'CO', 'COMPANY', 'COS',
    'LTD', 'LIMITED', 'LP', 'LLP', 'LLLP', 'PA', 'PLLC', 'PC', 'PL', 'THE', 'A', 'AN', 'OF',
    'AND', '&', 'DBA', 'D/B/A'}
# Words that carry industry meaning and should survive normalisation even though
# they're common — keep them so "ACME PLUMBING" != "ACME ROOFING".
KEEP = {'PLUMBING', 'HEATING', 'AIR', 'COOLING', 'ROOFING', 'ELECTRIC', 'ELECTRICAL',
        'LANDSCAPE', 'LANDSCAPING', 'CLEANING', 'PEST', 'AUTO', 'AUTOMOTIVE', 'BODY', 'DENTAL',
        'VETERINARY', 'INSURANCE', 'TRUCKING', 'MACHINE', 'SIGN', 'SIGNS', 'SPA', 'MEDICAL'}

_punct = re.compile(r"[^A-Z0-9 ]+")
_ws = re.compile(r"\s+")

def normalize_name(name: str) -> str:
    """Uppercase, strip punctuation and corporate suffixes, collapse whitespace."""
    if not isinstance(name, str):
        return ''
    s = name.upper().replace('&', ' AND ')
    s = _punct.sub(' ', s)
    toks = [t for t in _ws.split(s.strip()) if t]
    toks = [t for t in toks if t not in SUFFIXES or t in KEEP]
    return ' '.join(toks)

def name_key(name: str) -> str:
    return normalize_name(name).replace(' ', '')

def zip5(z) -> str:
    if not isinstance(z, str):
        return ''
    m = re.match(r"\s*(\d{5})", z)
    return m.group(1) if m else ''

def clean_city(c) -> str:
    return normalize_name(c) if isinstance(c, str) else ''

def ein_key(e) -> str:
    """Digits only; Sunbiz stores FEI with or without dash, 5500 stores 9 digits."""
    if not isinstance(e, str):
        return ''
    d = re.sub(r"\D", "", e)
    return d if len(d) == 9 else ''

def pick_col(df: pd.DataFrame, aliases) -> str | None:
    """Return the first column in df whose lowercase name matches an alias."""
    lower = {c.lower(): c for c in df.columns}
    for a in aliases:
        if a.lower() in lower:
            return lower[a.lower()]
    return None

def require_cols(df: pd.DataFrame, spec: dict, source: str) -> dict:
    """spec = {logical_name: [aliases]}. Returns mapping logical->actual. Raises if a required one is missing."""
    out = {}
    missing = []
    for logical, aliases in spec.items():
        col = pick_col(df, aliases)
        if col is None:
            missing.append(f"{logical} (tried {aliases})")
        else:
            out[logical] = col
    if missing:
        raise KeyError(f"{source}: could not find columns -> " + '; '.join(missing)
                       + f". Columns present: {list(df.columns)[:40]}")
    return out

def fuzzy_join(left: pd.DataFrame, right: pd.DataFrame, *, left_name: str, right_name: str,
               left_city: str, right_city: str, left_zip: str, right_zip: str,
               threshold: int = 88, right_prefix: str = 'r_') -> pd.DataFrame:
    """Blocked fuzzy join. Candidates share a 5-digit zip OR a normalised city.

    Returns left rows with the best right match appended (columns prefixed) plus
    match_score (0-100) and match_block ('zip'|'city'|'none').
    """
    from rapidfuzz import fuzz, process

    L = left.copy()
    R = right.copy()
    L['_nn'] = L[left_name].map(normalize_name)
    R['_nn'] = R[right_name].map(normalize_name)
    L['_zip'] = L[left_zip].map(zip5) if left_zip in L else ''
    R['_zip'] = R[right_zip].map(zip5) if right_zip in R else ''
    L['_city'] = L[left_city].map(clean_city) if left_city in L else ''
    R['_city'] = R[right_city].map(clean_city) if right_city in R else ''
    R = R[R['_nn'] != '']

    by_zip = {k: g for k, g in R.groupby('_zip') if k}
    by_city = {k: g for k, g in R.groupby('_city') if k}

    rows = []
    for _, lr in L.iterrows():
        best, best_score, block = None, 0, 'none'
        for key, pool, label in ((lr['_zip'], by_zip, 'zip'), (lr['_city'], by_city, 'city')):
            if not key or key not in pool:
                continue
            cand = pool[key]
            res = process.extractOne(lr['_nn'], cand['_nn'].tolist(), scorer=fuzz.token_sort_ratio)
            if res and res[1] > best_score:
                best_score = res[1]
                best = cand.iloc[res[2]]
                block = label
            if best_score >= 99:
                break
        rec = lr.to_dict()
        if best is not None and best_score >= threshold:
            for c in R.columns:
                if c.startswith('_'):
                    continue
                rec[right_prefix + c] = best[c]
            rec['match_score'] = int(best_score)
            rec['match_block'] = block
        else:
            rec['match_score'] = int(best_score) if best is not None else 0
            rec['match_block'] = 'none'
        rows.append(rec)
    out = pd.DataFrame(rows)
    return out.drop(columns=[c for c in out.columns if c.startswith('_')], errors='ignore')
