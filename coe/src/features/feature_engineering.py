"""Feature pipeline: structured machine context + multilingual note text -> sparse matrix."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.features.text_features import clean_note, normalise_note, detect_language
from src.utils.config import MACHINE_STATES

CATEGORICAL = ["machine_state", "previous_machine_state", "next_machine_state", "robot_mode", "safety_zone_status", "sensor_status",
               "material_status", "quality_status", "product", "shift", "workstation_id"]
NUMERIC = ["log_duration", "cycle_time_seconds", "note_missing"]
STRUCTURED_COLS = CATEGORICAL + NUMERIC
TEXT_COLS = ["note_norm", "note_raw"]


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns; tolerant of missing columns / unseen states (failure-state safe)."""
    d = df.copy()
    for c in CATEGORICAL:
        if c not in d:
            d[c] = "UNKNOWN"
        d[c] = d[c].fillna("UNKNOWN").astype(str)
    for c in ["machine_state", "previous_machine_state", "next_machine_state"]:
        d[c] = d[c].where(d[c].isin(set(MACHINE_STATES)), "UNKNOWN")
    dur = pd.to_numeric(d["stoppage_duration_seconds"] if "stoppage_duration_seconds" in d else pd.Series(0.0, index=d.index), errors="coerce").fillna(0).clip(lower=0)
    d["log_duration"] = np.log1p(dur)
    d["cycle_time_seconds"] = pd.to_numeric(d["cycle_time_seconds"] if "cycle_time_seconds" in d else pd.Series(75.0, index=d.index), errors="coerce").fillna(75.0)
    notes = d["operator_note"] if "operator_note" in d else pd.Series([""] * len(d), index=d.index)
    d["note_raw"] = notes.map(clean_note)
    d["note_norm"] = notes.map(normalise_note)
    d["note_missing"] = (d["note_raw"] == "").astype(float)
    d["note_lang"] = notes.map(detect_language)
    return d


def build_preprocessor(use_structured=True, use_text=True) -> ColumnTransformer:
    parts = []
    if use_structured:
        parts.append(("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL))
        parts.append(("num", StandardScaler(), NUMERIC))
    if use_text:
        parts.append(("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), "note_norm"))
        parts.append(("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, sublinear_tf=True), "note_raw"))
    return ColumnTransformer(parts)
