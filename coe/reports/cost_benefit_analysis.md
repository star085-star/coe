# Benefit vs Cost, Maintenance and Unintended Consequences

All dollar numbers use **assumptions** (edit `src/utils/config.py`), not plant data. Verified recovery figures come from `reports/results.json`.

## Measured / modelled benefit
* Verified actions recover ~3.9 stoppage-hours per day in the synthetic plant, ~1,275 h/yr.
* At an assumed $60 contribution margin per station-hour: ~$76k/yr. **Optimistic.**
* Year-1 cost ~$10.4k: build 120 h x $30 + $600 edge PC + 6 h/month upkeep + $4,000 fixture/lens hardware for the fixes.
* **Pessimistic sensitivity:** if a station-hour is worth only $10 and only 25% of recovered time becomes extra output, benefit = 1,275 x 10 x 0.25 = ~$3.2k/yr, which does **not** repay year-1 cost. The case depends on real downtime value; the pilot must measure it.

## Environmental
Idle cobot energy avoided is small (~320 kWh, ~226 kg CO2 per year at assumed 0.25 kW idle and 0.71 kg/kWh), so don't claim large energy savings. The more plausible environmental benefit is less scrap/rework from fixing misalignment and fewer re-runs; this was **not measured**.

## Social
Less repetitive manual resetting and fewer interruptions for operators; Tamil-language notes become *usable data* rather than ignored text; supervisors get evidence for fixture/tooling investment instead of blaming people.

## Maintenance burden
Model refresh monthly (1-2 h), re-label ~100 events per quarter (label-efficiency curve: ~0.82 macro-F1 with only 5% labelled), lexicon review by a native speaker twice a year, drift check on the share of abstained events. Runs on CPU in seconds.

## Unintended consequences and mitigations
| Risk | Mitigation |
|---|---|
| Used to monitor/discipline operators (operator ids correlate with causes) | Operator ID excluded from model features; dashboards group by station/shift/product only; policy statement agreed with workers' representatives |
| Over-trust of confident but wrong labels | Confidence shown, review queue, human sign-off required for VERIFIED |
| New cause confidently mislabelled (measured failure: unseen-cause abstention ~2%) | Weekly review of discovered clusters / low-margin events; do not auto-close actions |
| Notes become formulaic because operators "write for the system" | Notes optional; periodic audit of note quality |
| Alert fatigue / extra admin | No alerts; weekly review cadence |
| Language bias (Tamil/Tanglish under-served) | Per-language accuracy tracked every retrain |
| Chance findings from many comparisons | Bonferroni correction; effect-size threshold; minimum counts |
