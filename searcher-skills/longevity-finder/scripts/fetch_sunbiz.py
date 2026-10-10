#!/usr/bin/env python3
"""Florida Division of Corporations bulk registry: download over public SFTP and
parse the fixed-width Corporate Data File into a slim CSV of active entities.

The Division publishes the credentials on its own data-downloads page; they are
public by design. Files: quarterly snapshot split into ten parts (cordata*.zip),
roughly 1.7 GB each unzipped. This script streams them line by line, so memory
stays flat.

Usage:
  python fetch_sunbiz.py --outdir data                 # download + parse
  python fetch_sunbiz.py --local /path/to/zips --outdir data   # parse files you already have
  python fetch_sunbiz.py --sample /path/to/cordata0.txt        # print 5 parsed rows + date-format check
"""
import argparse, os, sys, io, zipfile, csv, re, posixpath
from datetime import date
from collections import Counter

HOST, PORT, USER, PASSWORD = 'sftp.floridados.gov', 22, 'Public', 'PubAccess1845!'

# (name, start_1based, length) — from the Division's published Corporate Data File Structure.
FIELDS = [
    ('cor_number', 1, 12), ('cor_name', 13, 192), ('status', 205, 1), ('filing_type', 206, 15),
    ('addr1', 221, 42), ('addr2', 263, 42), ('city', 305, 28), ('state', 333, 2), ('zip', 335, 10),
    ('country', 345, 2), ('mail_addr1', 347, 42), ('mail_addr2', 389, 42), ('mail_city', 431, 28),
    ('mail_state', 459, 2), ('mail_zip', 461, 10), ('mail_country', 471, 2), ('file_date', 473, 8),
    ('fei', 481, 14), ('more_officers', 495, 1), ('last_txn_date', 496, 8), ('state_country', 504, 2),
    ('report_year1', 506, 4), ('report_date1', 511, 8), ('report_year2', 519, 4), ('report_date2', 524, 8),
    ('report_year3', 532, 4), ('report_date3', 537, 8), ('ra_name', 545, 42), ('ra_type', 587, 1),
    ('ra_addr', 588, 42), ('ra_city', 630, 28), ('ra_state', 658, 2), ('ra_zip', 660, 9),
]
OFFICER_START, OFFICER_LEN = 669, 128
for i in range(1, 7):
    b = OFFICER_START + (i - 1) * OFFICER_LEN
    FIELDS += [(f'off{i}_title', b, 4), (f'off{i}_type', b + 4, 1), (f'off{i}_name', b + 5, 42),
               (f'off{i}_addr', b + 47, 42), (f'off{i}_city', b + 89, 28), (f'off{i}_state', b + 117, 2),
               (f'off{i}_zip', b + 119, 9)]
MIN_LINE = OFFICER_START + 6 * OFFICER_LEN - 1  # 1436

def parse_line(line: str) -> dict:
    rec = {}
    for name, start, length in FIELDS:
        rec[name] = line[start - 1:start - 1 + length].strip()
    return rec

def detect_date_format(samples):
    """Return 'YYYYMMDD' or 'MMDDYYYY' from a list of 8-char date strings."""
    y_first = sum(1 for s in samples if s[:4].isdigit() and 1800 <= int(s[:4]) <= date.today().year)
    y_last = sum(1 for s in samples if s[4:].isdigit() and 1800 <= int(s[4:]) <= date.today().year)
    return 'YYYYMMDD' if y_first >= y_last else 'MMDDYYYY'

def to_iso(s, fmt):
    if not s or len(s) != 8 or not s.isdigit():
        return ''
    if fmt == 'YYYYMMDD':
        y, m, d = s[:4], s[4:6], s[6:]
    else:
        m, d, y = s[:2], s[2:4], s[4:]
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return ''

def iter_lines(path):
    """Yield decoded lines from a .txt or every .txt inside a .zip."""
    if path.lower().endswith('.zip'):
        with zipfile.ZipFile(path) as zf:
            for member in zf.namelist():
                if member.lower().endswith('.txt'):
                    with zf.open(member) as fh:
                        for raw in io.TextIOWrapper(fh, encoding='latin-1', errors='replace'):
                            yield raw.rstrip('\r\n')
    else:
        with open(path, encoding='latin-1', errors='replace') as fh:
            for raw in fh:
                yield raw.rstrip('\r\n')

def sftp_fetch(outdir, pattern='cordata'):
    import paramiko
    os.makedirs(outdir, exist_ok=True)
    t = paramiko.Transport((HOST, PORT))
    t.connect(username=USER, password=PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(t)
    found = []
    def walk(d, depth):
        if depth > 4:
            return
        try:
            for e in sftp.listdir_attr(d):
                p = posixpath.join(d, e.filename)
                import stat as st
                if st.S_ISDIR(e.st_mode):
                    walk(p, depth + 1)
                elif pattern in e.filename.lower() and e.filename.lower().endswith(('.zip', '.txt')):
                    found.append(p)
        except IOError:
            pass
    walk('.', 0)
    if not found:
        print('No files containing', pattern, 'found on the SFTP server. Directory tree seen:')
        for e in sftp.listdir('.'):
            print('  ', e)
        sys.exit(1)
    local = []
    for p in found:
        dest = os.path.join(outdir, posixpath.basename(p))
        if not os.path.exists(dest):
            print('downloading', p)
            sftp.get(p, dest)
        local.append(dest)
    sftp.close(); t.close()
    return local

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outdir', default='data')
    ap.add_argument('--local', help='directory with cordata*.zip or *.txt already downloaded')
    ap.add_argument('--sample', help='parse the first rows of one file and print them')
    ap.add_argument('--status', default='A', help='status code to keep (A = active)')
    ap.add_argument('--keep-all-status', action='store_true')
    a = ap.parse_args()

    if a.sample:
        lines = []
        for ln in iter_lines(a.sample):
            lines.append(ln)
            if len(lines) >= 2000:
                break
        recs = [parse_line(l) for l in lines if len(l) >= 480]
        fmt = detect_date_format([r['file_date'] for r in recs if r['file_date']])
        print('line length (first):', len(lines[0]) if lines else None, '| expected >=', MIN_LINE)
        print('date format detected:', fmt)
        print('status codes in sample:', Counter(r['status'] for r in recs).most_common())
        print('filing types in sample:', Counter(r['filing_type'] for r in recs).most_common(8))
        for r in recs[:5]:
            print({k: r[k] for k in ('cor_number', 'cor_name', 'status', 'filing_type', 'city', 'state', 'file_date', 'fei', 'off1_title', 'off1_name')},
                  '-> file_date', to_iso(r['file_date'], fmt))
        return

    raw = os.path.join(a.outdir, 'raw'); os.makedirs(raw, exist_ok=True)
    if a.local:
        files = [os.path.join(a.local, f) for f in sorted(os.listdir(a.local)) if 'cordata' in f.lower()]
    else:
        files = sftp_fetch(raw)
    if not files:
        sys.exit('No cordata files to parse.')

    out = os.path.join(a.outdir, 'sunbiz_active.csv')
    cols = ['cor_number', 'cor_name', 'status', 'filing_type', 'addr1', 'city', 'state', 'zip', 'file_date_iso',
            'fei', 'last_txn_iso', 'report_year1', 'state_country', 'ra_name'] + \
           [f'off{i}_{k}' for i in range(1, 7) for k in ('title', 'name')]
    n_in = n_out = 0
    fmt = None
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for path in files:
            print('parsing', path)
            buf = []
            for line in iter_lines(path):
                if len(line) < 480:
                    continue
                n_in += 1
                rec = parse_line(line)
                if fmt is None:
                    buf.append(rec['file_date'])
                    if len(buf) >= 500:
                        fmt = detect_date_format([b for b in buf if b]); print('date format:', fmt)
                if not a.keep_all_status and rec['status'] != a.status:
                    continue
                rec['file_date_iso'] = to_iso(rec['file_date'], fmt or 'MMDDYYYY')
                rec['last_txn_iso'] = to_iso(rec['last_txn_date'], fmt or 'MMDDYYYY')
                w.writerow({c: rec.get(c, '') for c in cols})
                n_out += 1
    print(f'parsed {n_in:,} records, kept {n_out:,} with status {a.status} -> {out}')

if __name__ == '__main__':
    main()
