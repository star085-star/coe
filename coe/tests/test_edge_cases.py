"""Edge / failure cases: each must not crash and must degrade safely."""
import pandas as pd
from src.data.preprocess import preprocess_dataset


def _row(**kw):
    base = dict(machine_state="BLOCKED", previous_machine_state="RUNNING", next_machine_state="RUNNING", operator_note="sensor blocked by dust",
                product="Product_A", shift="Shift_1", workstation_id="WS_02", stoppage_duration_seconds=12.0, robot_mode="AUTOMATIC",
                safety_zone_status="CLEAR", sensor_status="BLOCKED", material_status="PRESENT", quality_status="PASS", cycle_time_seconds=70.0)
    base.update(kw); return pd.DataFrame([base])


def test_missing_operator_note(miner):
    p = miner.predict(_row(operator_note=None)).iloc[0]
    assert p.cause == "SENSOR_INTERRUPTION"          # structured signals still carry it


def test_unknown_machine_state_does_not_crash(miner):
    p = miner.predict(_row(machine_state="TOTALLY_NEW_STATE")).iloc[0]
    assert 0 <= p.confidence <= 1


def test_very_short_and_zero_duration(miner):
    assert len(miner.predict(_row(stoppage_duration_seconds=0.5))) == 1
    assert len(miner.predict(_row(stoppage_duration_seconds=0))) == 1


def test_mixed_tamil_tanglish_note(miner):
    p = miner.predict(_row(operator_note="சென்சார் தூசி clean panninom", machine_state="IDLE", sensor_status="OK")).iloc[0]
    assert p.cause == "SENSOR_INTERRUPTION"


def test_no_information_event_abstains(miner):
    row = pd.DataFrame([{"operator_note": ""}])
    p = miner.predict(row).iloc[0]
    assert p.cause == "UNKNOWN" or p.confidence < 0.6


def test_misleading_state_text_rescues(miner):
    # machine log says SAFETY_STOP but note + sensor flag say sensor issue
    p = miner.predict(_row(machine_state="SAFETY_STOP", operator_note="sensor block aachu")).iloc[0]
    assert p.cause in {"SENSOR_INTERRUPTION", "SAFETY_ZONE_INTERRUPTION"}


def test_duplicate_and_negative_cleaned(tmp_path):
    raw = tmp_path / "r.csv"
    pd.DataFrame([{"event_id": "A", "timestamp": "2026-08-01 10:00:00", "stoppage_duration_seconds": 5, "operator_note": None, "machine_state": "X",
                   "previous_machine_state": "RUNNING", "next_machine_state": "RUNNING"}] * 2 +
                 [{"event_id": "B", "timestamp": "2026-08-01 10:00:01", "stoppage_duration_seconds": -3, "operator_note": "", "machine_state": "IDLE",
                   "previous_machine_state": "RUNNING", "next_machine_state": "RUNNING"}]).to_csv(raw, index=False)
    out = preprocess_dataset(raw, tmp_path / "p.csv", sample_path=None, verbose=False)
    assert len(out) == 1 and out.iloc[0].machine_state == "UNKNOWN"


def test_verification_without_post_period_returns_empty(clean_df):
    from src.evaluation.corrective_actions import verify_actions
    early = clean_df[clean_df.period == "PRE"]
    assert verify_actions(early, "verified_root_cause") == []
