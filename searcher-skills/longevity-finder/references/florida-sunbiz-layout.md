# Florida Division of Corporations — Corporate Data File

Source: Florida Department of State, Division of Corporations, "Data Downloads" and "Corporate Data File Structure" pages (dos.fl.gov/sunbiz/other-services/data-downloads/). Public, free, no account.

## Access
- SFTP host `sftp.floridados.gov`, username `Public`, password `PubAccess1845!` — published by the Division on the downloads page for public use.
- Also reachable in a browser through the Division's Data Access Portal with the same credentials, if SFTP is blocked on the searcher's network. Download the quarterly `cordata*` files into a folder and run `fetch_sunbiz.py --local <folder>`.
- Quarterly snapshot (January, April, July, October) = all active data at generation time, split into ten files by last digit of the document number. Each is roughly 1.7 GB unzipped. Daily files carry only that day's additions and are not needed for this skill.

## Record layout (fixed width, 1-based positions, as published)
| Field | Start | Len |
|---|---|---|
| Corporation Number | 1 | 12 |
| Corporation Name | 13 | 192 |
| Status | 205 | 1 |
| Filing Type | 206 | 15 |
| Address 1 / 2 | 221 / 263 | 42 / 42 |
| City / State / Zip / Country | 305 / 333 / 335 / 345 | 28 / 2 / 10 / 2 |
| Mail Address 1 / 2 | 347 / 389 | 42 / 42 |
| Mail City / State / Zip / Country | 431 / 459 / 461 / 471 | 28 / 2 / 10 / 2 |
| File Date | 473 | 8 |
| FEI Number | 481 | 14 |
| More than six officers flag | 495 | 1 |
| Last Transaction Date | 496 | 8 |
| State/Country of incorporation | 504 | 2 |
| Report Year 1 / Date 1 | 506 / 511 | 4 / 8 |
| Report Year 2 / Date 2 | 519 / 524 | 4 / 8 |
| Report Year 3 / Date 3 | 532 / 537 | 4 / 8 |
| Registered Agent Name / Type / Address | 545 / 587 / 588 | 42 / 1 / 42 |
| RA City / State / Zip (inferred from the gap before Officer 1) | 630 / 658 / 660 | 28 / 2 / 9 |
| Officer n (n = 1..6): Title / Name Type / Name / Address / City / State / Zip | 669 + 128·(n−1), then +4, +5, +47, +89, +117, +119 | 4 / 1 / 42 / 42 / 28 / 2 / 9 |

Officer title codes published by the Division: P President, V Vice President, T Treasurer, S Secretary, C Chairman, D Director. Files in the wild also carry four-letter titles (PRES, VP, MGR, etc.); keep the raw value.

## Things to check on first run (the script prints these with `--sample`)
- Date format of File Date: the script auto-detects MMDDYYYY vs YYYYMMDD from the first 500 rows. Confirm the printed detection makes sense (charter years should mostly be 1950–today).
- Status code for active entities. The script defaults to `A`; the `--sample` output lists the codes present. Adjust `--status` if the distribution says otherwise.
- "File Date" is the registry charter date. A business re-incorporated (LLC conversion, new entity after a sale) shows a young charter even if the trade name is decades old. The 7(a) `BusinessAge` field and the website's "since 19xx" (handled by `transition-signals`) corroborate or contradict it.
