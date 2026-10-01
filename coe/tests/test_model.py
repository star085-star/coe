import pandas as pd
from sklearn.metrics import f1_score
from src.baseline.baseline_model import RuleBasedFrequencyBaseline
from src.evaluation.corrective_actions import verify_actions
from src.evaluation.hidden_downtime import hidden_downtime
from src.features.text_features import detect_language, normalise_note


def test_prototype_beats_baseline(clean_df, miner):
    test = clean_df.sample(frac=0.4, random_state=2)
    y = test.verified_root_cause
    fb = f1_score(y, RuleBasedFrequencyBaseline().predict(test), average="macro")
    fp = f1_score(y, miner.predict(test).cause, average="macro")
    assert fp > fb + 0.10


def test_language_detection_and_normalisation():
    assert detect_language("") == "none"
    assert detect_language("சென்சார் தூசி அடைப்பு") == "ta"
    assert detect_language("sensor block aachu") == "tanglish"
    assert detect_language("sensor blocked by dust") == "en"
    assert "CT_SENSOR" in normalise_note("சென்சார் தூசி அடைப்பு") and "CT_SENSOR" in normalise_note("Sensor Blocked")


def test_patterns_ranked_and_have_context(clean_df, miner):
    pred = miner.predict(clean_df)
    pats = miner.mine_patterns(clean_df, pred)
    assert len(pats) >= 4 and pats[0]["pattern_id"] == "P-01"
    assert [p["priority_score"] for p in pats] == sorted([p["priority_score"] for p in pats], reverse=True)
    mis = next(p for p in pats if p["cause"] == "MATERIAL_MISALIGNMENT")
    assert any(v["value"] == "Product_A" for v in mis["context"].get("product", []))  # injected pattern is recovered


def test_hidden_downtime_only_counts_generic_codes(clean_df):
    h = hidden_downtime(clean_df, "verified_root_cause")
    assert 0 < h["hidden_events"] < len(clean_df)


def test_verification_verifies_effective_and_not_ineffective(clean_df):
    res = {v["cause"]: v for v in verify_actions(clean_df, "verified_root_cause")}
    assert res["SENSOR_INTERRUPTION"]["status"] == "VERIFIED"
    assert res["ROBOT_RECOVERY"]["status"] != "VERIFIED"      # deliberately ineffective action
    assert res["TOOL_CHANGE"]["status"] == "NO_ACTION"
