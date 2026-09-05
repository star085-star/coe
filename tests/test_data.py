try:
    import pytest
except ImportError:
    pytest = None
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data.generate_dataset import generate_synthetic_dataset
from src.data.validation import validate_raw_dataset
from src.data.preprocess import preprocess_dataset
from src.utils.config import RAW_DATA_PATH, PROCESSED_DATA_PATH

def test_dataset_generation():
    """Verify synthetic dataset generation produces expected schema and non-empty dataframe."""
    df = generate_synthetic_dataset(num_records=100)
    assert len(df) >= 100
    assert "event_id" in df.columns
    assert "stoppage_duration_seconds" in df.columns
    assert "operator_note" in df.columns

def test_data_validation():
    """Verify validation report catches raw dataset issues."""
    df = pd.DataFrame([
        {"event_id": "EVT_001", "stoppage_duration_seconds": 10.0, "operator_note": "test note", "machine_state": "RUNNING"},
        {"event_id": "EVT_001", "stoppage_duration_seconds": -5.0, "operator_note": "", "machine_state": "INVALID_STATE"}
    ])
    report = validate_raw_dataset(df)
    assert report["duplicate_event_ids"] == 1
    assert report["invalid_durations_lte_zero"] == 1
    assert report["missing_operator_notes"] == 1

def test_preprocessing_pipeline(tmp_path):
    """Verify preprocessor deduplicates records and removes non-positive durations."""
    raw_path = tmp_path / "raw.csv"
    proc_path = tmp_path / "proc.csv"
    
    df_raw = pd.DataFrame([
        {"event_id": "EVT_001", "timestamp": "2026-08-01 10:00:00", "stoppage_duration_seconds": 15.0, "operator_note": "note 1", "machine_state": "RUNNING", "previous_machine_state": "RUNNING", "next_machine_state": "RUNNING"},
        {"event_id": "EVT_001", "timestamp": "2026-08-01 10:01:00", "stoppage_duration_seconds": 20.0, "operator_note": "dup note", "machine_state": "RUNNING", "previous_machine_state": "RUNNING", "next_machine_state": "RUNNING"},
        {"event_id": "EVT_002", "timestamp": "2026-08-01 10:02:00", "stoppage_duration_seconds": -10.0, "operator_note": "bad dur", "machine_state": "RUNNING", "previous_machine_state": "RUNNING", "next_machine_state": "RUNNING"}
    ])
    df_raw.to_csv(raw_path, index=False)
    
    df_clean = preprocess_dataset(input_path=raw_path, output_path=proc_path)
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["event_id"] == "EVT_001"
    assert df_clean.iloc[0]["stoppage_duration_seconds"] == 15.0
