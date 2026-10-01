# 3-Minute Demo Video Script (record this; no video is included in the repo)

Set up: `python run_pipeline.py && uvicorn backend.main:app --port 8000`, open http://127.0.0.1:8000. Screen-record with voice-over.

| Time | Screen | Say |
|---|---|---|
| 0:00-0:20 | Slide / README top | "Micro-stoppages are logged as generic downtime, so recurring causes are invisible. 88% of stoppage time in my synthetic plant is hidden this way." |
| 0:20-0:50 | Overview tab | "Hidden downtime by cause. Baseline lumps by machine state; my miner uses states, notes, product, shift, duration." |
| 0:50-1:25 | Patterns tab | "Top pattern: operator loading delay on Shift 3; misalignment on WS_01 with Product A on Shift 2. Each has a recommended action." |
| 1:25-1:55 | Live triage, then toggle தமிழ் | Type "சென்சார் தூசி அடைப்பு" then "sensor block aachu": show cause, evidence; then empty form -> "needs human review". |
| 1:55-2:25 | Corrective-actions tab | "Pre/post rate with confidence interval. Four actions verified; robot-recovery fix correctly NOT effective. Supervisor signs off." |
| 2:25-2:50 | Evaluation tab | "Macro-F1 0.90 vs 0.50 baseline; 7 of 9 targets met. Two fail: unseen causes and lost notes+sensors - I report them." |
| 2:50-3:00 | README | "Code, tests, reports in the repo. Limits: synthetic data, validation pending." |
