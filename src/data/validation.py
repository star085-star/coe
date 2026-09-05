import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.utils.config import MACHINE_STATES

def validate_raw_dataset(df: pd.DataFrame) -> dict:
    """
    Validates data quality, schema integrity, and flags anomalies.
    Returns a dictionary summarizing validation metrics and health checks.
    """
    total_records = len(df)
    
    # 1. Duplicate Check
    duplicate_events = df.duplicated(subset=["event_id"]).sum()
    
    # 2. Duration Anomalies
    invalid_durations = (df["stoppage_duration_seconds"] <= 0).sum()
    null_durations = df["stoppage_duration_seconds"].isna().sum()
    extremely_short = ((df["stoppage_duration_seconds"] > 0) & (df["stoppage_duration_seconds"] <= 2.0)).sum()
    
    # 3. Missing Notes
    missing_notes = df["operator_note"].isna().sum() + (df["operator_note"].astype(str).str.strip() == "").sum()
    
    # 4. Unknown / Anomalous Machine States
    known_states = set(MACHINE_STATES)
    unknown_states = df[~df["machine_state"].isin(known_states)]["machine_state"].nunique()
    
    # 5. Null values across key columns
    null_counts = df.isna().sum().to_dict()
    
    report = {
        "total_records": total_records,
        "duplicate_event_ids": int(duplicate_events),
        "invalid_durations_lte_zero": int(invalid_durations),
        "null_durations": int(null_durations),
        "extremely_short_durations_lte_2s": int(extremely_short),
        "missing_operator_notes": int(missing_notes),
        "missing_operator_notes_pct": round(missing_notes / total_records * 100, 2),
        "unknown_machine_state_types": int(unknown_states),
        "null_counts": null_counts,
        "is_passed": (invalid_durations == 0 and duplicate_events == 0)
    }
    return report

if __name__ == "__main__":
    from src.utils.config import RAW_DATA_PATH
    df = pd.read_csv(RAW_DATA_PATH)
    val_report = validate_raw_dataset(df)
    print("Dataset Validation Health Report:")
    for k, v in val_report.items():
        print(f"  {k}: {v}")
