import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

class RuleBasedFrequencyBaseline:
    """
    Baseline Model: Uses simple rule-based frequency analysis grouping by
    machine_state + product + shift to identify top recurring downtime combinations.
    """
    def __init__(self):
        self.group_rankings = None

    def fit(self, df: pd.DataFrame):
        """
        Groups dataset by machine_state + product + shift and aggregates occurrence count,
        avg duration, and total downtime.
        """
        grouped = df.groupby(["machine_state", "product", "shift"]).agg(
            occurrences=("event_id", "count"),
            avg_duration_sec=("stoppage_duration_seconds", "mean"),
            total_downtime_sec=("stoppage_duration_seconds", "sum")
        ).reset_index()

        # Sort by total downtime descending
        grouped = grouped.sort_values(by="total_downtime_sec", ascending=False).reset_index(drop=True)
        grouped["avg_duration_sec"] = grouped["avg_duration_sec"].round(1)
        grouped["total_downtime_sec"] = grouped["total_downtime_sec"].round(1)
        
        self.group_rankings = grouped
        return grouped

    def predict_cause_for_event(self, row: pd.Series) -> str:
        """
        Baseline heuristic cause mapping based purely on machine state and basic attributes.
        """
        state = str(row.get("machine_state", ""))
        sec = float(row.get("stoppage_duration_seconds", 0.0))

        if state == "WAITING_FOR_OPERATOR":
            if row.get("product") == "Product_A":
                return "MATERIAL_MISALIGNMENT"
            else:
                return "OPERATOR_LOADING_DELAY"
        elif state in ["ERROR", "BLOCKED"]:
            return "SENSOR_INTERRUPTION"
        elif state == "SAFETY_STOP":
            return "SAFETY_ZONE_INTERRUPTION"
        elif state == "RECOVERY":
            return "ROBOT_RECOVERY"
        elif state == "TOOL_CHANGE":
            return "TOOL_CHANGE"
        elif state == "INSPECTION_HOLD":
            return "QUALITY_INSPECTION_DELAY"
        elif state == "IDLE":
            return "MATERIAL_SHORTAGE"
        else:
            return "UNKNOWN"

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """
        Predicts root cause for a DataFrame of events.
        """
        return df.apply(self.predict_cause_for_event, axis=1)

if __name__ == "__main__":
    from src.utils.config import PROCESSED_DATA_PATH
    df = pd.read_csv(PROCESSED_DATA_PATH)
    baseline = RuleBasedFrequencyBaseline()
    rankings = baseline.fit(df)
    print("Baseline Top 10 Recurring Combinations:")
    print(rankings.head(10))
