# Rubric — the three questions, answered from evidence only

For each target, read the evidence columns in `ranked_targets.csv` (and the pages you fetched yourself) and answer three questions with a probability from 0 to 1. Write them to `judgements.csv` with columns:
`business_name, owner_operated_p, named_successor_p, retirement_p, notes`

Then re-run `score_signals.py --judgements judgements.csv` so the ranking uses your read instead of the heuristics.

## 1. Does the owner still do the work or run the floor? (`owner_operated_p`)
High (0.8+): owner named on the site as the person who answers the phone / does estimates / is "on every job"; one or two registry officers; headcount under ~15; reviews or testimonials name the owner as the technician.
Mid (0.4–0.6): owner named as founder or president but a service manager, office manager, or crew leads are also named.
Low (≤0.2): a management team page with titles, hiring pages, multiple locations, officers who are clearly not family and hold operating titles.

## 2. Is there a named successor? (`named_successor_p`)
High: "second/third generation", "son/daughter joined the business", two officers with the same surname where one carries JR/II/III, a younger family member named as GM/VP of operations.
Mid: two officers share a surname with no generational marker (often a spouse — a co-owner, not a successor); a non-family GM named.
Low: single officer, no family language, no GM named, site says "owner-operated" in the present tense.

## 3. Any retirement or transition language? (`retirement_p`)
High: "retiring", "after 40 years", "looking for the right person to carry on", "under new ownership" (already transitioned — a *different* kind of hit: note it), "for sale".
Mid: "celebrating 45 years", a site that looks untouched since the last redesign, an owner who speaks about legacy.
Low: active hiring, recent expansion, new location, new fleet, recent copyright year and modern stack.

## What not to do
- Don't infer anyone's age from their name, photo, or anything else. Longevity of the *business* is the signal; the person's age is not yours to guess.
- Don't use people-search sites, voter files, or property records to profile owners. Public corporate officer data is the limit of this pack.
- Don't treat "no website" as a negative. Many excellent 40-year-old trade businesses have none. It means less evidence, not a worse target.
- Keep `notes` short and quote the evidence. The searcher will read it before a cold approach.
