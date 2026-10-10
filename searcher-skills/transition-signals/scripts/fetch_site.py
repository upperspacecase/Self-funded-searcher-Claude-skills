#!/usr/bin/env python3
"""Fetch each target's website (home + about/team/history pages) and extract
transition signals with evidence snippets. Plain HTTP only — no APIs, no scrapers
of protected sites.

Input: a CSV with at least business_name, and a `website` column (filled by the
searcher's Claude Code session via web search, or left blank — blank rows are
skipped and reported).

Usage:
  python fetch_site.py --input survivors.csv --out site_signals.csv --limit 100
"""
import argparse, re, sys, time
from urllib.parse import urljoin, urlparse
import requests
import pandas as pd
from bs4 import BeautifulSoup

UA = {'User-Agent': 'Mozilla/5.0 (compatible; searcher-skills/1.0; research use)'}
ABOUT_WORDS = ('about', 'our-story', 'ourstory', 'history', 'team', 'our-team', 'who-we-are', 'company', 'meet')

PATTERNS = {
    'founded_year': r'\b(?:since|established(?: in)?|founded(?: in)?|est\.?|serving [a-z ,]{0,40} since)\s*((?:18|19|20)\d\d)\b',
    'years_in_business': r'\b(\d{2})\+?\s*years? (?:in business|of experience|of service|serving)|\bfor (?:over |more than |nearly )?(\d{2})\+? years\b',
    'family_owned': r'family[- ](?:owned|operated|run)',
    'generation': r'\b(?:second|third|fourth|2nd|3rd|4th)[- ]generation\b',
    'retire': r'\bretir(?:e|ed|ing|ement)\b',
    'succession_words': r'\b(?:took over|taking over|now run by|has taken the reins|passed the torch|carries on|carry on the)\b',
    'son_daughter': r'\b(?:his son|her son|his daughter|her daughter|our son|our daughter|sons|daughters)\b',
    'owner_operated': r'\bowner[- ]operat(?:ed|or)\b|\bthe owner\b|\bowner and operator\b',
    'hiring': r'\b(?:now hiring|join our team|we are hiring|careers)\b',
    'new_ownership': r'\b(?:under new (?:ownership|management)|new owners?)\b',
    'for_sale': r'\b(?:business for sale|for sale)\b',
}
MODERN = {
    'booking_widget': r'servicetitan|housecallpro|housecall pro|getjobber|jobber|calendly|acuityscheduling|booksy|vagaro|mindbody|setmore|square(?:up)?\.com/appointments',
    'chat_widget': r'intercom|drift\.com|tidio|livechat|podium|birdeye|tawk\.to',
    'ad_pixel': r'googletagmanager|gtag\(|fbq\(|fbevents\.js|google-analytics\.com|analytics\.js',
    'social_links': r'facebook\.com/|instagram\.com/|tiktok\.com/|youtube\.com/|linkedin\.com/',
    'reviews_widget': r'reviews?\.io|trustpilot|birdeye|podium|nicejob|reviewbuzz',
}

def fetch(url, timeout=20):
    try:
        r = requests.get(url, headers=UA, timeout=timeout, allow_redirects=True)
        if r.status_code >= 400:
            return None, f'HTTP {r.status_code}'
        return r, None
    except requests.RequestException as e:
        return None, str(e)[:120]

def text_of(html):
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script', 'style', 'noscript']):
        t.decompose()
    return re.sub(r'\s+', ' ', soup.get_text(' ')).strip(), soup

def snippets(text, pattern, width=90, max_n=3):
    out = []
    for m in re.finditer(pattern, text, re.I):
        s = max(0, m.start() - width); e = min(len(text), m.end() + width)
        out.append('…' + text[s:e].strip() + '…')
        if len(out) >= max_n:
            break
    return out

def analyse(base_url, officers):
    r, err = fetch(base_url)
    if r is None:
        return {'fetch_status': err}
    final = r.url
    pages = {final: r.text}
    text, soup = text_of(r.text)
    # follow a few about-like links on the same host
    host = urlparse(final).netloc
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if any(w in href for w in ABOUT_WORDS):
            u = urljoin(final, a['href'])
            if urlparse(u).netloc == host and u not in pages and len(pages) < 5:
                rr, _ = fetch(u)
                if rr is not None:
                    pages[u] = rr.text
                time.sleep(0.5)
    all_html = '\n'.join(pages.values())
    all_text = ' '.join(text_of(h)[0] for h in pages.values())

    rec = {'fetch_status': 'ok', 'final_url': final, 'pages_fetched': len(pages), 'https': final.startswith('https'),
           'text_chars': len(all_text)}
    gen = soup.find('meta', attrs={'name': 'generator'})
    rec['site_generator'] = (gen.get('content', '') if gen else '')[:60]
    rec['has_viewport_meta'] = bool(soup.find('meta', attrs={'name': 'viewport'}))
    cp = re.findall(r'(?:©|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d\d)', all_text, re.I)
    rec['copyright_year'] = max(map(int, cp)) if cp else ''
    for k, p in PATTERNS.items():
        hits = snippets(all_text, p)
        rec[k] = len(hits)
        rec[k + '_evidence'] = ' | '.join(hits)
    fy = re.findall(PATTERNS['founded_year'], all_text, re.I)
    rec['founded_year_value'] = min(map(int, fy)) if fy else ''
    for k, p in MODERN.items():
        rec[k] = bool(re.search(p, all_html, re.I))
    # officer surnames on the site = owner still fronts the business
    surn = [s.strip().upper() for s in officers if s]
    found = [s for s in surn if s and re.search(r'\b' + re.escape(s) + r'\b', all_text, re.I)]
    rec['officer_surnames_on_site'] = ', '.join(found)
    rec['officer_surname_hit'] = bool(found)
    return rec

def officer_surnames(officers_field):
    out = []
    if not isinstance(officers_field, str):
        return out
    for item in officers_field.split(';'):
        name = item.split(':', 1)[-1].strip()
        if ',' in name:
            out.append(name.split(',')[0].strip())
        elif name:
            out.append(name.split()[-1])
    return list(dict.fromkeys(out))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', default='site_signals.csv')
    ap.add_argument('--limit', type=int, default=200)
    a = ap.parse_args()
    df = pd.read_csv(a.input, dtype=str, keep_default_na=False)
    if 'website' not in df.columns:
        sys.exit("Input has no 'website' column. Add one (fill it for the rows you want analysed) and re-run.")
    rows = []
    todo = df[df['website'].str.strip() != ''].head(a.limit)
    print(f'{len(todo)} rows with a website; {len(df) - len(todo)} without (skipped).')
    for i, r in todo.iterrows():
        url = r['website'].strip()
        if not url.startswith('http'):
            url = 'https://' + url
        rec = {'business_name': r.get('business_name', ''), 'website': url}
        rec.update(analyse(url, officer_surnames(r.get('officers', ''))))
        rows.append(rec)
        print(f"  {rec['business_name'][:40]:40} {rec.get('fetch_status')}")
        time.sleep(1.0)
    pd.DataFrame(rows).to_csv(a.out, index=False)
    print('->', a.out)

if __name__ == '__main__':
    main()
