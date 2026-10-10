"""Offline tests: run with `python -m pytest tests -q` or `python tests/test_longevity.py`."""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
from common import normalize_name, ein_key, zip5
from fetch_sunbiz import parse_line, FIELDS, MIN_LINE, detect_date_format, to_iso
import pandas as pd

def test_normalize():
    assert normalize_name('The Lee Thompson Co., Inc.') == 'LEE THOMPSON'
    assert normalize_name('Fox & Hearn, Inc') == 'FOX HEARN'
    assert normalize_name('ACME PLUMBING INC') != normalize_name('ACME ROOFING INC')

def test_keys():
    assert ein_key('59-1234567') == '591234567' and ein_key('abc') == ''
    assert zip5('33131-2200') == '33131'

def _line(vals):
    line = [' '] * (MIN_LINE + 10)
    for name, start, length in FIELDS:
        v = vals.get(name, '')[:length].ljust(length)
        line[start - 1:start - 1 + length] = list(v)
    return ''.join(line)

def test_sunbiz_parse():
    r = parse_line(_line({'cor_number': 'P84000012345', 'cor_name': 'ADVENT AIR CONDITIONING, INC.', 'status': 'A', 'city': 'TAMPA', 'state': 'FL', 'zip': '33602', 'file_date': '03151984', 'fei': '59-1234567', 'off1_title': 'PRES', 'off1_name': 'SMITH, JOHN A', 'off6_name': 'LAST, ONE'}))
    assert r['cor_name'] == 'ADVENT AIR CONDITIONING, INC.' and r['status'] == 'A' and r['fei'] == '59-1234567'
    assert r['off1_title'] == 'PRES' and r['off1_name'] == 'SMITH, JOHN A' and r['off6_name'] == 'LAST, ONE'
    fmt = detect_date_format(['03151984', '12012001'])
    assert fmt == 'MMDDYYYY' and to_iso('03151984', fmt) == '1984-03-15'
    assert to_iso('19840315', 'YYYYMMDD') == '1984-03-15'

def test_pipeline_on_fixtures(tmp_path=None):
    subprocess.run([sys.executable, os.path.join(HERE, 'make_fixtures.py')], check=True)
    d = os.path.join(HERE, 'fixtures', 'data')
    out = os.path.join(d, 'surv_test.csv')
    subprocess.run([sys.executable, os.path.join(HERE, '..', 'scripts', 'build_survivors.py'), '--state', 'FL', '--naics', '238220', '--min-years', '30', '--mode', 'sba-first', '--datadir', d, '--out', out], check=True)
    df = pd.read_csv(out)
    names = set(df['business_name'])
    assert 'THE LEE THOMPSON CO' in names and 'ADVENT AIR CONDITIONING, INC.' in names
    assert 'NEWCO PLUMBING LLC' not in names, 'too young, must be excluded'
    adv = df[df['business_name'].str.startswith('ADVENT')].iloc[0]
    assert adv['headcount_source'] == '5500 via EIN' and int(adv['headcount_5500']) == 39
    assert bool(adv['family_surname_signal']) is True
    assert os.path.exists(out.replace('.csv', '_unmatched_sba.csv'))

if __name__ == '__main__':
    for fn in (test_normalize, test_keys, test_sunbiz_parse, test_pipeline_on_fixtures):
        fn(); print('PASS', fn.__name__)
