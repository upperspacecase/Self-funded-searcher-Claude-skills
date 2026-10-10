# survivors.csv — column meanings

| Column | Meaning | Source |
|---|---|---|
| business_name | Legal name as registered | state registry (or SBA borrower name if no registry match) |
| city, state, zip | Principal address | registry / SBA |
| charter_date | Formation date on the registry | registry File Date |
| years_registered | Whole years since charter_date | derived |
| filing_type | Registry entity type code (e.g. DOMP domestic profit corp, FLAL Florida LLC) | registry |
| registry_doc_number | Registry document number — paste into the state's search page to verify by hand | registry |
| last_annual_report_year | Most recent annual report year on file | registry |
| naics | NAICS code from the SBA loan record | SBA |
| naics_5500 | Business code the employer reported on Form 5500 (6-digit NAICS) | DOL |
| sba_loan_count, sba_first_loan_year, sba_last_loan_year, sba_max_loan | SBA loan history (PPP + 7(a)) | SBA |
| ppp_est_annual_payroll | PPP loan ÷ 2.5 × 12 — a 2020-era payroll estimate, approximate | derived |
| ppp_jobs | Jobs reported on the PPP application | SBA |
| ppp_not_fully_forgiven | PPP forgiveness < 98% of the loan — worth a question, not a verdict | derived |
| sba7a_business_age | SBA's own business-age category on the 7(a) record, where present | SBA |
| headcount_5500 | Active plan participants (or beginning-of-year participants) on the latest Form 5500 — only employers with a benefit plan appear | DOL |
| headcount_source | "5500 via EIN" (exact) or "5500 via name (score)" (fuzzy) | derived |
| officers | title:name pairs from the registry, up to six | registry |
| officer_count | Number of officers listed | registry |
| family_surname_signal | True if two or more officers share a surname | derived |
| industry_evidence | registry-first only: which signal put this entity in the industry (name, 5500, sba) | derived |
| match_score, match_block | Fuzzy match score (0–100) and the blocking key that produced it (zip or city) | derived |
| match_evidence | Plain-language summary of how the row was assembled | derived |

A companion file `*_unmatched_sba.csv` lists SBA borrowers in the industry that found no registry match. Read it: the names there are real businesses the pipeline lost, and a scan often shows why (DBA names, out-of-state parent, typos).
