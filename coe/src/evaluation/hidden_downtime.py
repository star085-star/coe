"""Hidden-downtime accounting: downtime that the MES logged only under a generic code."""
import pandas as pd
from src.utils.config import (GENERIC_MES_CODE, COST_PER_STATION_HOUR_USD, OPERATING_DAYS_PER_YEAR, COBOT_IDLE_KW,
                              GRID_KG_CO2_PER_KWH)


def hidden_downtime(df: pd.DataFrame, cause_col: str) -> dict:
    """Attribute generic-coded downtime to causes using `cause_col` (predicted or true)."""
    h = df[df["mes_reason_code"] == GENERIC_MES_CODE]
    span_days = (pd.to_datetime(df["timestamp"]).max() - pd.to_datetime(df["timestamp"]).min()).total_seconds() / 86400
    by = h.groupby(cause_col)["stoppage_duration_seconds"].agg(["count", "sum"]).rename(columns={"count": "events", "sum": "seconds"})
    by["hours"] = (by["seconds"] / 3600).round(2)
    by["share_pct"] = (100 * by["seconds"] / by["seconds"].sum()).round(1)
    total_h = h["stoppage_duration_seconds"].sum() / 3600
    annual_h = total_h / span_days * OPERATING_DAYS_PER_YEAR
    return {
        "hidden_events": int(len(h)), "hidden_hours": round(total_h, 2),
        "hidden_share_of_all_downtime_pct": round(100 * h["stoppage_duration_seconds"].sum() / df["stoppage_duration_seconds"].sum(), 1),
        "span_days": round(span_days, 1), "annualised_hours_scaled": round(annual_h, 1),
        "annualised_cost_usd": round(annual_h * COST_PER_STATION_HOUR_USD),
        "annualised_idle_kwh": round(annual_h * COBOT_IDLE_KW), "annualised_co2_kg": round(annual_h * COBOT_IDLE_KW * GRID_KG_CO2_PER_KWH),
        "by_cause": by.reset_index().rename(columns={cause_col: "cause"}).to_dict("records"),
    }


def correct_attribution_share(df: pd.DataFrame, pred_col: str, true_col="verified_root_cause") -> float:
    """Share of hidden-downtime seconds attributed to the correct true cause (abstentions count as wrong)."""
    h = df[df["mes_reason_code"] == GENERIC_MES_CODE]
    ok = h.loc[h[pred_col] == h[true_col], "stoppage_duration_seconds"].sum()
    return float(ok / h["stoppage_duration_seconds"].sum())
