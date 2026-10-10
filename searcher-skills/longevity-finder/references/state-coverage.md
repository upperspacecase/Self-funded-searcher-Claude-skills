# State coverage

The SBA and Form 5500 stages are national. Only the registry stage is state-specific.

| State | Registry bulk data | Status in this pack |
|---|---|---|
| Florida | Free public SFTP, fixed-width layout published, includes FEI and six officers | **Supported** — `fetch_sunbiz.py` |
| Others | Varies: some states publish open bulk files, some sell them, some only offer a CAPTCHA-protected web search | Not yet. See below. |

## Adding a state
Write `fetch_<state>.py` that produces `data/registry_<ST>_active.csv` with these columns:
`cor_number, cor_name, status, filing_type, addr1, city, state, zip, file_date_iso, fei, last_txn_iso, report_year1, state_country, ra_name, off1_title, off1_name … off6_title, off6_name`.
Leave `fei` blank if the state doesn't publish it (matching to Form 5500 then falls back to name + city). Register the script in `run_state.py` under `REGISTRY_FETCHERS`.

Before writing an adapter, verify on the state's own site: whether bulk data is downloadable, the cost, the format, and whether officers and formation date are included. Do not guess. If a state has no bulk option, say so to the searcher and offer `registry-first` with a different registry proxy — or stop at the SBA stage, which still yields borrower name, city, NAICS, loan size and year.
