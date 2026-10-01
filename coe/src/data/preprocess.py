import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    SAMPLE_DATA_PATH,
    MACHINE_STATES
)
from src.data.validation import validate_raw_dataset

def preprocess_dataset(input_path: Path = RAW_DATA_PATH, output_path: Path = PROCESSED_DATA_PATH, sample_path=SAMPLE_DATA_PATH, verbose=True) -> pd.DataFrame:
    """
    Cleans raw micro-stoppage dataset:
    - Deduplicates records by event_id
    - Drops invalid/impossible durations (<= 0)
    - Safely maps unknown machine states to 'UNKNOWN'
    - Fills missing operator notes with empty strings
    - Converts timestamp to datetime
    - Saves cleaned dataset to processed and sample paths
    """
    if verbose:
        print(f"Loading raw dataset from {input_path}...")
    df = pd.read_csv(input_path)
    initial_len = len(df)
    
    # 1. Deduplicate by event_id (keep first)
    df = df.drop_duplicates(subset=["event_id"], keep="first").copy()
    dedup_len = len(df)
    
    # 2. Handle invalid durations: drop non-positive or null durations
    df = df[df["stoppage_duration_seconds"] > 0].copy()
    valid_dur_len = len(df)
    
    # 3. Clean and fill missing operator notes
    df["operator_note"] = df["operator_note"].fillna("").astype(str).str.strip()
    
    # 4. Standardize Machine States (map unrecognized states to 'UNKNOWN')
    known_states = set(MACHINE_STATES)
    df["machine_state"] = df["machine_state"].apply(lambda s: s if s in known_states else "UNKNOWN")
    df["previous_machine_state"] = df["previous_machine_state"].apply(lambda s: s if s in known_states else "UNKNOWN")
    df["next_machine_state"] = df["next_machine_state"].apply(lambda s: s if s in known_states else "UNKNOWN")
    
    # 5. Timestamp conversion
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Save processed dataset
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    # Also save a 500-record sample for fast previewing & testing
    if sample_path is not None:
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        df.head(500).to_csv(sample_path, index=False)
    
    if not verbose:
        return df
    print(f"Preprocessing Complete:")
    print(f"  Initial records: {initial_len}")
    print(f"  After deduplication: {dedup_len}")
    print(f"  After filtering invalid durations (> 0s): {valid_dur_len}")
    print(f"  Processed dataset saved to {output_path}")
    print(f"  Sample dataset saved to {SAMPLE_DATA_PATH}")
    
    return df

if __name__ == "__main__":
    df_clean = preprocess_dataset()
