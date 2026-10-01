import pytest
from fastapi.testclient import TestClient
from backend.main import app

c = TestClient(app)


def test_endpoints_ok():
    for p in ["/health", "/kpis", "/patterns", "/causes", "/downtime", "/corrective-actions", "/evaluation", "/errors", "/events?limit=3", "/"]:
        assert c.get(p).status_code == 200, p


def test_classify_multilingual_and_empty():
    r = c.post("/classify", json={"machine_state": "BLOCKED", "operator_note": "சென்சார் தூசி அடைப்பு", "stoppage_duration_seconds": 12}).json()
    assert r["note_language"] == "ta" and r["cause"] == "SENSOR_INTERRUPTION"
    e = c.post("/classify", json={}).json()
    assert e["needs_human_review"] is True


def test_validation_errors():
    assert c.post("/classify", json={"stoppage_duration_seconds": -5}).status_code == 422
    assert c.post("/verify-action", json={"action_id": "CA-01", "confirmed_by": "x", "decision": "MAYBE"}).status_code == 422
    assert c.get("/patterns/P-99").status_code == 404
