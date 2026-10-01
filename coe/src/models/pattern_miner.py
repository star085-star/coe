"""Micro-stoppage pattern miner.

Stage 1  cause attribution  : regularised logistic regression on structured context + multilingual note text,
                              trained on the small maintenance-verified subset; abstains below a confidence threshold.
Stage 2  pattern mining     : groups attributed events into recurring patterns (cause x station/shift/product context,
                              recurrence across days, downtime share) and ranks them by hidden downtime.
Stage 3  discovery          : clusters abstained (low-confidence) events so new, unseen causes surface for review.
Logistic regression was chosen over deeper models because labels are scarce, CPU-only edge deployment is required,
and per-prediction explanations ("because note says 'sensor block' + sensor_status=BLOCKED") can be shown to operators.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.features.feature_engineering import build_preprocessor, prepare_frame
from src.utils.config import ABSTAIN_THRESHOLD, ACTION_LIBRARY, RANDOM_SEED, GENERIC_MES_CODE


class MicroStoppageMiner:
    def __init__(self, threshold=ABSTAIN_THRESHOLD, use_structured=True, use_text=True, C=3.0):
        self.threshold = threshold
        self.pipe = Pipeline([
            ("prep", build_preprocessor(use_structured, use_text)),
            ("clf", LogisticRegression(C=C, max_iter=3000, class_weight="balanced")),
        ])
        self.fitted = False

    # ---- stage 1 -------------------------------------------------------
    @staticmethod
    def augment(df: pd.DataFrame, seed=RANDOM_SEED) -> pd.DataFrame:
        """Failure-state augmentation: blank notes, drop status flags, jitter durations (labels unchanged)."""
        rng = np.random.default_rng(seed)
        a = df.copy()
        m = rng.random(len(a)) < 0.30
        a.loc[m, "operator_note"] = ""
        m = rng.random(len(a)) < 0.30
        for c, v in [("sensor_status", "OK"), ("material_status", "PRESENT"), ("safety_zone_status", "CLEAR"), ("quality_status", "PASS")]:
            if c in a:
                a.loc[m, c] = v
        a["stoppage_duration_seconds"] = a["stoppage_duration_seconds"] * np.exp(rng.normal(0, 0.7, len(a)))
        return a

    def fit(self, df: pd.DataFrame, label_col="verified_root_cause", augment=True):
        X = pd.concat([df, self.augment(df)]) if augment else df
        self.pipe.fit(prepare_frame(X), X[label_col].values)
        self.classes_ = list(self.pipe.named_steps["clf"].classes_)
        self.fitted = True
        return self

    def predict_proba(self, df):
        return self.pipe.predict_proba(prepare_frame(df))

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Returns DataFrame[cause, confidence, raw_cause] indexed like df. Abstains -> cause='UNKNOWN'."""
        P = self.predict_proba(df)
        idx = P.argmax(1)
        conf = P.max(1)
        raw = np.array(self.classes_)[idx]
        cause = np.where(conf < self.threshold, "UNKNOWN", raw)
        return pd.DataFrame({"cause": cause, "confidence": conf.round(3), "raw_cause": raw}, index=df.index)

    def explain(self, df_row: pd.DataFrame, top=5):
        """Top features pushing the prediction (coefficient x feature value) for a single-row frame."""
        X = self.pipe.named_steps["prep"].transform(prepare_frame(df_row))
        clf = self.pipe.named_steps["clf"]
        names = self.pipe.named_steps["prep"].get_feature_names_out()
        k = int(clf.predict_proba(X).argmax())
        contrib = np.asarray(X.multiply(clf.coef_[k]).todense()).ravel()
        order = np.argsort(-contrib)[:top]
        return [(names[i].split("__", 1)[-1], round(float(contrib[i]), 3)) for i in order if contrib[i] > 0]

    # ---- stage 2 -------------------------------------------------------
    def mine_patterns(self, df: pd.DataFrame, pred: pd.DataFrame, min_events=25):
        d = df.drop(columns=["confidence", "pred_cause"], errors="ignore").join(pred[["cause", "confidence"]].rename(columns={"cause": "pred_cause"}))
        d["ts"] = pd.to_datetime(d["timestamp"])
        d["day"] = d["ts"].dt.date
        total_dt = d["stoppage_duration_seconds"].sum()
        n_days = d["day"].nunique()
        pats = []
        for cause, g in d[d.pred_cause != "UNKNOWN"].groupby("pred_cause"):
            if len(g) < min_events:
                continue
            ctx = {}
            for dim in ["workstation_id", "shift", "product"]:
                share = g[dim].value_counts(normalize=True)
                base = d[dim].value_counts(normalize=True)
                keep = [(v, round(float(s), 2), round(float(s / base[v]), 2)) for v, s in share.items() if s >= 0.30 and s / base[v] >= 1.4]
                if keep:
                    ctx[dim] = [{"value": v, "share": s, "lift": l} for v, s, l in keep]
            note_terms = (g["note_norm"] if "note_norm" in g else g["operator_note"].fillna("")).astype(str)
            pats.append({
                "cause": cause, "events": int(len(g)), "downtime_hours": round(g["stoppage_duration_seconds"].sum() / 3600, 2),
                "downtime_share_pct": round(100 * g["stoppage_duration_seconds"].sum() / total_dt, 1),
                "mean_duration_sec": round(g["stoppage_duration_seconds"].mean(), 1),
                "days_active": int(g["day"].nunique()), "recurrence_ratio": round(g["day"].nunique() / n_days, 2),
                "mean_confidence": round(float(g["confidence"].mean()), 3),
                "top_machine_state": g["machine_state"].value_counts().index[0],
                "context": ctx, "recommended_action": ACTION_LIBRARY[cause]["text"], "action_id": ACTION_LIBRARY[cause]["action_id"],
                "priority_score": round(g["stoppage_duration_seconds"].sum() * g["confidence"].mean() / 3600, 2),
            })
        pats.sort(key=lambda p: -p["priority_score"])
        for i, p in enumerate(pats, 1):
            p["pattern_id"] = f"P-{i:02d}"
        return pats

    # ---- stage 3 -------------------------------------------------------
    def discover_unknown_clusters(self, df: pd.DataFrame, pred: pd.DataFrame, k=3, min_events=30):
        """Cluster abstained events so novel causes are surfaced for human review."""
        low = df[pred["cause"] == "UNKNOWN"]
        if len(low) < min_events:
            return []
        X = self.pipe.named_steps["prep"].transform(prepare_frame(low))
        k = min(k, max(1, len(low) // min_events))
        lab = KMeans(n_clusters=k, n_init=5, random_state=RANDOM_SEED).fit_predict(X)
        out = []
        for c in range(k):
            g = low[lab == c]
            out.append({"cluster": c, "events": int(len(g)), "downtime_hours": round(g["stoppage_duration_seconds"].sum() / 3600, 2),
                        "top_state": g["machine_state"].value_counts().index[0], "top_workstation": g["workstation_id"].value_counts().index[0],
                        "example_notes": [n for n in g["operator_note"].fillna("").astype(str).head(20) if n][:3]})
        return sorted(out, key=lambda x: -x["events"])
