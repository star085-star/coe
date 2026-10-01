"""Closed-loop verification of corrective actions using pre/post stoppage RATES per operating hour.

For each mined pattern with an implemented action we compare events/hour before and after the go-live time.
Under H0 (no change) the number of post events, given the total, is Binomial(N, T_post / (T_pre + T_post));
an exact one-sided binomial test gives the p-value and a Clopper-Pearson interval gives a CI on the reduction.
  VERIFIED     : reduction >= 30% and p < 0.01
  NOT_EFFECTIVE: reduction < 10% or p >= 0.05          (action should be revisited / rejected)
  INCONCLUSIVE : otherwise
Alpha is Bonferroni-corrected over the number of causes tested (added after a chance false-verification was
observed on a control cause in the first run; see reports/evaluation_report.md).
Control causes (no action implemented) are tested the same way to measure the false-verification rate.
"""
import pandas as pd
from scipy.stats import binomtest

from src.utils.config import (POST_START, ACTION_LIBRARY, VERIFY_MIN_REDUCTION, VERIFY_ALPHA, REJECT_ALPHA, REJECT_MAX_REDUCTION)


def _rate_test(n_pre, n_post, t_pre, t_post):
    N = n_pre + n_post
    if N == 0:
        return None
    frac = t_post / (t_pre + t_post)
    res = binomtest(n_post, N, frac, alternative="less")
    ci = binomtest(n_post, N, frac).proportion_ci(confidence_level=0.95)
    ratio = lambda p: (p / (1 - p)) * (t_pre / t_post) if p < 1 else float("inf")
    r_pre, r_post = n_pre / t_pre, n_post / t_post
    return {"rate_pre_per_h": round(r_pre, 3), "rate_post_per_h": round(r_post, 3),
            "reduction_pct": round(100 * (1 - r_post / r_pre), 1) if r_pre else 0.0, "p_value": float(res.pvalue),
            "reduction_ci95_pct": [round(100 * (1 - ratio(ci.high)), 1), round(100 * (1 - ratio(ci.low)), 1)]}


def verify_actions(df: pd.DataFrame, cause_col: str, bonferroni=True) -> list:
    d = df.copy()
    d["ts"] = pd.to_datetime(d["timestamp"])
    post = pd.Timestamp(POST_START)
    t_pre = (post - d["ts"].min()).total_seconds() / 3600
    t_post = (d["ts"].max() - post).total_seconds() / 3600
    if t_pre <= 0 or t_post <= 0:   # go-live time is outside the data: nothing to verify
        return []
    n_tests = len([c for c in ACTION_LIBRARY if c != 'UNKNOWN'])
    k = n_tests if bonferroni else 1   # Bonferroni: 8 causes tested at once
    out = []
    for cause, meta in ACTION_LIBRARY.items():
        if cause == "UNKNOWN":
            continue
        g = d[d[cause_col] == cause]
        r = _rate_test((g["ts"] < post).sum(), (g["ts"] >= post).sum(), t_pre, t_post)
        if r is None:
            continue
        pre_sec = g.loc[g["ts"] < post, "stoppage_duration_seconds"].sum() / t_pre
        post_sec = g.loc[g["ts"] >= post, "stoppage_duration_seconds"].sum() / t_post
        red, p = r["reduction_pct"] / 100, r["p_value"]
        status = "VERIFIED" if (red >= VERIFY_MIN_REDUCTION and p < VERIFY_ALPHA / k) else \
                 "NOT_EFFECTIVE" if (red < REJECT_MAX_REDUCTION or p >= REJECT_ALPHA) else "INCONCLUSIVE"
        if not meta["implemented"]:
            status = "NO_ACTION"
        out.append({"cause": cause, "action_id": meta["action_id"], "action": meta["text"], "implemented": meta["implemented"],
                    "n_pre": int((g["ts"] < post).sum()), "n_post": int((g["ts"] >= post).sum()), **r,
                    "hidden_seconds_saved_per_day": round((pre_sec - post_sec) * 24, 1), "status": status,
                    "stat_status_if_tested": status if meta["implemented"] else ("WOULD_VERIFY" if (red >= VERIFY_MIN_REDUCTION and p < VERIFY_ALPHA / k) else "NO_CHANGE")})
    return out
