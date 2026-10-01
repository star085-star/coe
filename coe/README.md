# Micro-Stoppage Pattern Miner for Human + Cobot Plants

Capstone prototype: finds the **recurring causes hiding behind micro-stoppages** that an MES records only as generic downtime, and
closes the loop by **verifying that corrective actions actually reduced them**.

> **Data is synthetic** (generator in `src/data/generate_dataset.py`). All numbers below are measured by the code in this repo,
> but they show the *pipeline works on a realistic simulation*, not that it will score the same in a real plant. Stakeholder validation is **pending** (see below).

## What it does
1. **Cleans** raw events (dedupe, negative/zero durations, unknown machine states).
2. **Attributes** each stop to a root cause from machine states, operator notes (English / Tanglish / Tamil), product, shift, station and duration. Abstains when unsure.
3. **Mines patterns**: cause x station/shift/product context, recurrence across days, hidden-downtime hours, recommended action.
4. **Verifies actions**: events/hour before vs after go-live, exact binomial test (Bonferroni-corrected) + 95% CI -> `VERIFIED / NOT_EFFECTIVE / INCONCLUSIVE`, then human sign-off.
5. **Dashboard** (EN/தமிழ், high-contrast, text-size, keyboard) + REST API + live triage form.

## Results (single run, seed 42; labelled events = 30%, evaluated on the other 70%)
| Metric | Baseline | Target | Measured | |
|---|---|---|---|---|
| Cause macro-F1 | 0.504 | >= 0.80 | **0.899** | PASS |
| Gain over baseline | - | >= +0.10 | **+0.394** | PASS |
| Hidden downtime attributed to correct cause | 0.512 | >= 0.80 | **0.923** | PASS |
| Top-4 cause downtime error | 23.1% | <= 10% | **2.4%** | PASS |
| Effective actions correctly VERIFIED | 1.0 | >= 0.75 | **1.0** | PASS |
| Ineffective action not verified | 1.0 | = 1.0 | **1.0** | PASS |
| Mean reduction of verified actions | - | >= 30% | **54.6%** | PASS |
| Worst macro-F1 drop in failure states | 0.086 | <= 0.15 | **0.176** | **FAIL** |
| Unseen cause not confidently mislabelled | 0 | >= 0.50 | **0.018** | **FAIL** |

* 5 independently generated datasets: prototype macro-F1 0.88 (0.87-0.89) vs baseline ~0.50; no false verifications; action-effect estimate error 2.1 pp vs 7.4 pp for the baseline. Both failures repeat in every seed.
* The baseline *also* verifies the effective actions; the prototype's advantage is in **accurate cause attribution and effect estimates**, not in pass/fail alone.
* **Honest notes:** (1) after the first run I added training-time augmentation and a Bonferroni correction (disclosed in the report); (2) the failing cases are discussed in `reports/evaluation_report.md` - lost notes+sensor flags is information-limited, and a confidence threshold does not catch a brand-new cause; (3) injected effect sizes are my assumptions.

Full detail: [`reports/evaluation_report.md`](reports/evaluation_report.md), [`reports/error_analysis.md`](reports/error_analysis.md).

## Deliverables map
| Required | Where |
|---|---|
| Problem analysis | `docs/problem_analysis.md` |
| User & workflow map | `docs/user_workflow_map.md` |
| Cleaned / synthetic dataset | `data/raw`, `data/processed`, `data/sample` (+ generator) |
| Working prototype | `src/`, `backend/`, `frontend/` |
| Baseline | `src/baseline/baseline_model.py` |
| Test cases (>=3 edge/failure) | `tests/` (19 tests) + failure-state experiments in the evaluation |
| Evaluation report (baseline, target, measured, error analysis) | `reports/` |
| Accessibility & multilingual | `docs/accessibility_multilingual.md`, `frontend/index.html` |
| Cost/benefit/unintended consequences | `reports/cost_benefit_analysis.md` |
| Stakeholder validation | `reports/stakeholder_validation.md` - **protocol only, results to be collected** |
| 3-minute demo video | `DEMO_SCRIPT.md` - **script only; video must be recorded** |

## Run it
```bash
pip install -r requirements.txt
python run_pipeline.py              # generate -> clean -> train -> evaluate -> reports (+ --multi-seed)
python run_tests.py                 # 19 tests
uvicorn backend.main:app --port 8000   # dashboard at http://127.0.0.1:8000, API docs at /docs
```

## Why this approach
Labels are scarce (only verified events), so a **regularised linear model on sparse features** reaches 0.82 macro-F1 with 5% labels, runs on a CPU edge PC, and can show
*why* ("sensor_status=BLOCKED + note mentions dust") - important for trust. Character n-grams plus a small lexicon handle Tamil, Tanglish and typos without translation.
A baseline that trusts `machine_state` fails because the same state hides several causes. Verification uses a rate test per operating hour so that changing volumes don't fake an improvement.

## Layout
```
src/data        generate_dataset.py preprocess.py validation.py
src/features    text_features.py feature_engineering.py
src/baseline    baseline_model.py
src/models      pattern_miner.py
src/evaluation  evaluate.py hidden_downtime.py corrective_actions.py report.py
backend/main.py FastAPI + static dashboard      frontend/index.html
tests/  docs/  reports/  scripts/multi_seed.py  DEMO_SCRIPT.md
```

## Ethics
The system describes machines, fixtures and processes, **not people**: operator ID is not a model feature and is not shown. Do not use it for performance management.

## Known limitations
Synthetic data; Tamil strings not professionally reviewed; no voice input; no real screen-reader or operator testing yet; one simulated plant; dollar figures are illustrative.
