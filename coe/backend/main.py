"""FastAPI service + static dashboard.  uvicorn backend.main:app --port 8000"""
import json
import sys
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.features.text_features import detect_language
from src.utils.config import RESULTS_PATH, PROCESSED_DIR, SIGNOFF_PATH, ACTION_LIBRARY, BASE_DIR

app = FastAPI(title="Micro-Stoppage Pattern Miner", version="1.0")
_state = {}


def _load():
    if not _state:
        if not RESULTS_PATH.exists() or not (PROCESSED_DIR / "miner.joblib").exists():
            from src.data.generate_dataset import generate_synthetic_dataset
            from src.data.preprocess import preprocess_dataset
            from src.evaluation.evaluate import run
            generate_synthetic_dataset(); preprocess_dataset(); run()
        _state["R"] = json.load(open(RESULTS_PATH))
        _state["miner"] = joblib.load(PROCESSED_DIR / "miner.joblib")
        _state["events"] = pd.read_csv(PROCESSED_DIR / "events_scored.csv")
    return _state


class EventIn(BaseModel):
    machine_state: str = "UNKNOWN"
    previous_machine_state: str = "UNKNOWN"
    next_machine_state: str = "UNKNOWN"
    operator_note: Optional[str] = ""
    product: str = "UNKNOWN"
    shift: str = "UNKNOWN"
    workstation_id: str = "UNKNOWN"
    stoppage_duration_seconds: float = Field(30.0, ge=0, le=3600)
    robot_mode: str = "UNKNOWN"
    safety_zone_status: str = "UNKNOWN"
    sensor_status: str = "UNKNOWN"
    material_status: str = "UNKNOWN"
    quality_status: str = "UNKNOWN"
    cycle_time_seconds: float = 75.0


class SignOff(BaseModel):
    action_id: str
    confirmed_by: str = Field(..., min_length=1)
    decision: str = Field(..., pattern="^(CONFIRM|REJECT)$")
    comment: str = ""


@app.get("/health")
def health():
    s = _load(); return {"status": "ok", "events": len(s["events"])}


@app.get("/kpis")
def kpis():
    R = _load()["R"]; gt = R["hidden_downtime"]["deployed_estimate"]
    return {"events": R["n_events"], "hidden_downtime_hours": gt["hidden_hours"], "hidden_share_pct": gt["hidden_share_of_all_downtime_pct"],
            "annualised_cost_usd": gt["annualised_cost_usd"], "patterns": len(R["patterns"]),
            "verified_actions": sum(c["status"] == "VERIFIED" for c in R["corrective_actions"]),
            "prototype_macro_f1": R["prototype"]["macro_f1"], "baseline_macro_f1": R["baseline"]["macro_f1"]}


@app.get("/patterns")
def patterns():
    return _load()["R"]["patterns"]


@app.get("/patterns/{pattern_id}")
def pattern(pattern_id: str):
    for p in _load()["R"]["patterns"]:
        if p["pattern_id"] == pattern_id:
            return p
    raise HTTPException(404, "pattern not found")


@app.get("/causes")
def causes():
    return _load()["R"]["hidden_downtime"]["deployed_estimate"]["by_cause"]


@app.get("/downtime")
def downtime():
    return _load()["R"]["hidden_downtime"]


@app.get("/corrective-actions")
def actions():
    so = json.load(open(SIGNOFF_PATH)) if SIGNOFF_PATH.exists() else {}
    return [{**a, "human_signoff": so.get(a["action_id"])} for a in _load()["R"]["corrective_actions"]]


@app.post("/verify-action")
def verify_action(s: SignOff):
    ids = {m["action_id"] for m in ACTION_LIBRARY.values()}
    if s.action_id not in ids:
        raise HTTPException(404, "unknown action_id")
    so = json.load(open(SIGNOFF_PATH)) if SIGNOFF_PATH.exists() else {}
    so[s.action_id] = s.model_dump()
    SIGNOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(so, open(SIGNOFF_PATH, "w"), indent=1)
    return {"saved": True, "action_id": s.action_id}


@app.get("/evaluation")
def evaluation():
    R = _load()["R"]; return {k: R[k] for k in ["targets", "baseline", "prototype", "ablation_macro_f1", "failure_states", "unseen_cause", "label_efficiency", "verification_benchmark", "cost_benefit"]}


@app.get("/errors")
def errors():
    return _load()["R"]["error_analysis"]


@app.get("/events")
def events(limit: int = Query(50, le=500), offset: int = 0, shift: Optional[str] = None, product: Optional[str] = None, cause: Optional[str] = None):
    d = _load()["events"]
    if shift: d = d[d["shift"] == shift]
    if product: d = d[d["product"] == product]
    if cause: d = d[d["cause_hat"] == cause]
    cols = ["event_id", "timestamp", "workstation_id", "machine_state", "operator_note", "product", "shift", "stoppage_duration_seconds", "cause_hat", "confidence"]
    return {"total": len(d), "items": d.iloc[offset:offset + limit][cols].fillna("").to_dict("records")}


@app.post("/classify")
def classify(e: EventIn):
    """Live triage of a single stoppage. Works with missing/unknown fields; abstains when unsure."""
    s = _load(); row = pd.DataFrame([e.model_dump()])
    pred = s["miner"].predict(row).iloc[0]
    P = s["miner"].predict_proba(row)[0]
    top = sorted(zip(s["miner"].classes_, P), key=lambda x: -x[1])[:3]
    cause = pred["cause"]
    return {"cause": cause, "confidence": float(pred["confidence"]), "needs_human_review": bool(cause == "UNKNOWN" or pred["confidence"] < 0.6),
            "note_language": detect_language(e.operator_note), "top3": [{"cause": c, "p": round(float(p), 3)} for c, p in top],
            "evidence": [{"feature": f, "weight": w} for f, w in s["miner"].explain(row)], "suggested_action": ACTION_LIBRARY[cause]["text"]}


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "frontend" / "index.html")
