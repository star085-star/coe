"""End-to-end experiment. Run:  python -m src.evaluation.evaluate
Writes reports/results.json, reports/figures/*.png, data/processed/events_scored.csv, miner.joblib."""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.baseline.baseline_model import RuleBasedFrequencyBaseline
from src.evaluation.corrective_actions import verify_actions
from src.evaluation.hidden_downtime import correct_attribution_share, hidden_downtime
from src.features.feature_engineering import prepare_frame
from src.models.pattern_miner import MicroStoppageMiner
from src.utils.config import *

LABEL = "verified_root_cause"
KNOWN = [c for c in VERIFIED_ROOT_CAUSES if c != "UNKNOWN"]


def mf1(y, p):
    return float(f1_score(y, p, average="macro", labels=VERIFIED_ROOT_CAUSES, zero_division=0))


# ---------------------------------------------------------------- failure-state perturbations
def _corrupt(text, rng, frac=0.25):
    return "".join(ch for ch in str(text) if rng.random() > frac)


def perturbations(seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    def missing_notes(d):
        d = d.copy(); d["operator_note"] = ""; return d
    def unknown_states(d):
        d = d.copy(); m = rng.random(len(d)) < 0.30; d.loc[m, "machine_state"] = "NOT_A_KNOWN_STATE"; return d
    def sensor_dropout(d):
        d = d.copy(); m = rng.random(len(d)) < 0.60
        d.loc[m, ["sensor_status", "material_status", "safety_zone_status", "quality_status"]] = ["OK", "PRESENT", "CLEAR", "PASS"]; return d
    def garbled_notes(d):
        d = d.copy(); m = rng.random(len(d)) < 0.5
        d.loc[m, "operator_note"] = d.loc[m, "operator_note"].fillna("").map(lambda t: _corrupt(t, rng)); return d
    def duration_drift(d):
        d = d.copy(); d["stoppage_duration_seconds"] = d["stoppage_duration_seconds"] * 3; return d
    def notes_and_sensors_down(d):
        return sensor_dropout(missing_notes(d))
    return {"missing_notes": missing_notes, "unknown_machine_states_30pct": unknown_states, "sensor_flag_dropout_60pct": sensor_dropout,
            "garbled_notes_50pct": garbled_notes, "duration_drift_x3": duration_drift, "notes_and_sensor_flags_both_lost": notes_and_sensors_down}


def run(df: pd.DataFrame = None, seed=RANDOM_SEED, save=True):
    if df is None:
        df = pd.read_csv(PROCESSED_DATA_PATH)
    R = {"n_events": int(len(df)), "n_pre": int((df.period == "PRE").sum()), "n_post": int((df.period == "POST").sum())}
    train, test = train_test_split(df, train_size=LABELED_FRACTION, stratify=df[LABEL], random_state=seed)
    R["n_labeled_train"], R["n_test"] = int(len(train)), int(len(test))
    base = RuleBasedFrequencyBaseline()
    y = test[LABEL]

    # ---- 1. baseline vs prototype
    miner = MicroStoppageMiner().fit(train)
    pt = miner.predict(test)
    pb = base.predict(test)
    P, Rc, F, S = precision_recall_fscore_support(y, pt.cause, labels=VERIFIED_ROOT_CAUSES, zero_division=0)
    Pb, Rb, Fb, _ = precision_recall_fscore_support(y, pb, labels=VERIFIED_ROOT_CAUSES, zero_division=0)
    R["baseline"] = {"accuracy": round(accuracy_score(y, pb), 4), "macro_f1": round(mf1(y, pb), 4)}
    R["prototype"] = {"accuracy": round(accuracy_score(y, pt.cause), 4), "macro_f1": round(mf1(y, pt.cause), 4),
                      "abstain_rate": round(float((pt.cause == "UNKNOWN").mean()), 4),
                      "top2_accuracy": round(float(np.mean([y.iloc[i] in [miner.classes_[j] for j in np.argsort(-r)[:2]] for i, r in enumerate(miner.predict_proba(test))])), 4)}
    R["per_cause"] = [{"cause": c, "support": int(s), "proto_precision": round(p, 3), "proto_recall": round(r, 3), "proto_f1": round(f, 3),
                       "base_f1": round(fb, 3)} for c, p, r, f, s, fb in zip(VERIFIED_ROOT_CAUSES, P, Rc, F, S, Fb)]
    cm = confusion_matrix(y, pt.cause, labels=VERIFIED_ROOT_CAUSES)
    R["confusion_matrix"] = {"labels": VERIFIED_ROOT_CAUSES, "matrix": cm.tolist()}

    # ---- 2. ablation
    R["ablation_macro_f1"] = {"structured_only": round(mf1(y, MicroStoppageMiner(use_text=False).fit(train).predict(test).cause), 4),
                              "text_only": round(mf1(y, MicroStoppageMiner(use_structured=False).fit(train).predict(test).cause), 4),
                              "structured_plus_text": R["prototype"]["macro_f1"]}

    # ---- 3. label-efficiency (3 seeds)
    le = []
    for frac in [0.02, 0.05, 0.10, 0.30, 0.50]:
        sc = []
        for s in range(3):
            tr, te = train_test_split(df, train_size=frac, stratify=df[LABEL], random_state=100 + s)
            sc.append(mf1(te[LABEL], MicroStoppageMiner().fit(tr).predict(te).cause))
        le.append({"labeled_fraction": frac, "macro_f1_mean": round(float(np.mean(sc)), 4), "macro_f1_std": round(float(np.std(sc)), 4)})
    R["label_efficiency"] = le

    # ---- 4. failure states
    fs = []
    for name, fn in perturbations(seed).items():
        tp = fn(test)
        f_proto, f_base = mf1(y, miner.predict(tp).cause), mf1(y, base.predict(prepare_frame(tp)))
        fs.append({"failure_state": name, "proto_macro_f1": round(f_proto, 4), "proto_drop": round(R["prototype"]["macro_f1"] - f_proto, 4),
                   "base_macro_f1": round(f_base, 4), "base_drop": round(R["baseline"]["macro_f1"] - f_base, 4)})
    # unseen cause: retrain without MATERIAL_SHORTAGE, see what happens to its events
    held = "MATERIAL_SHORTAGE"
    m2 = MicroStoppageMiner().fit(train[train[LABEL] != held])
    p2 = m2.predict(test[test[LABEL] == held])
    unseen = {"held_out_cause": held, "events": int(len(p2)), "abstained_or_unknown_rate": round(float((p2.cause == "UNKNOWN").mean()), 4),
              "misattributed_to_recurring_cause_rate": round(float((p2.cause != "UNKNOWN").mean()), 4),
              "note": "Unseen cause is routed to UNKNOWN/review instead of being confidently mislabelled"}
    R["failure_states"], R["unseen_cause"] = fs, unseen

    # ---- 5. error analysis
    d = test.copy(); d["pred"] = pt.cause.values; d["conf"] = pt.confidence.values
    d = d.join(prepare_frame(test)[["note_lang"]])
    d["ok"] = d.pred == d[LABEL]
    typical = train.groupby(LABEL)["machine_state"].agg(lambda s: s.value_counts().index[0])
    d["state_typical"] = d.apply(lambda r: r["machine_state"] == typical.get(r[LABEL]), axis=1)
    R["error_analysis"] = {
        "accuracy_by_note_language": {k: {"n": int(len(g)), "accuracy": round(float(g.ok.mean()), 3)} for k, g in d.groupby("note_lang")},
        "accuracy_when_machine_state_matches_typical": round(float(d[d.state_typical].ok.mean()), 3),
        "accuracy_when_machine_state_is_misleading": round(float(d[~d.state_typical].ok.mean()), 3),
        "baseline_accuracy_when_state_misleading": round(float(np.mean(pb[~d.state_typical.values].values == y[~d.state_typical.values].values)), 3),
        "mean_confidence_correct": round(float(d[d.ok].conf.mean()), 3), "mean_confidence_wrong": round(float(d[~d.ok].conf.mean()), 3),
        "top_confusions": [{"true": t, "predicted": p, "count": int(n)} for (t, p), n in
                           d[~d.ok].groupby([LABEL, "pred"]).size().sort_values(ascending=False).head(6).items()],
        "example_errors": [{"event_id": r.event_id, "true": r[LABEL], "predicted": r.pred, "confidence": float(r.conf), "state": r.machine_state,
                            "note": r.operator_note if isinstance(r.operator_note, str) else "", "why": miner.explain(test.loc[[i]])}
                           for i, r in d[~d.ok].sort_values("conf", ascending=False).head(5).iterrows()],
    }

    # ---- 6. deployed attribution over ALL events: verified labels where they exist, predictions elsewhere
    allp = miner.predict(df)
    df = df.copy()
    df["cause_hat"] = np.where(df.event_id.isin(train.event_id), df[LABEL], allp.cause)
    df["confidence"] = np.where(df.event_id.isin(train.event_id), 1.0, allp.confidence)
    df["baseline_cause"] = base.predict(df)
    df["note_lang"] = prepare_frame(df)["note_lang"]

    # top-cause downtime attribution (test set)
    t_true = test.groupby(LABEL)["stoppage_duration_seconds"].sum()
    def attr(pred):
        t_pred = test.assign(p=pred.values).groupby("p")["stoppage_duration_seconds"].sum()
        rows = {c: round(100 * abs(t_pred.get(c, 0) - t_true[c]) / t_true[c], 1) for c in t_true.sort_values(ascending=False).index if c != "UNKNOWN"}
        top4 = list(rows)[:4]
        return {"error_pct_by_cause": rows, "top4_mean_error_pct": round(float(np.mean([rows[c] for c in top4])), 1),
                "spearman_rank": round(float(spearmanr([t_true.get(c, 0) for c in KNOWN], [t_pred.get(c, 0) for c in KNOWN])[0]), 3)}
    R["downtime_attribution"] = {"prototype": attr(pt.cause), "baseline": attr(pb)}

    # hidden downtime
    tt = test.assign(proto=pt.cause.values, base=pb.values)
    R["hidden_downtime"] = {"prototype_correct_share": round(correct_attribution_share(tt, "proto"), 4),
                            "baseline_correct_share": round(correct_attribution_share(tt, "base"), 4),
                            "ground_truth_summary": hidden_downtime(df, LABEL), "deployed_estimate": hidden_downtime(df, "cause_hat")}

    # ---- 7. corrective-action verification benchmark
    truth = {v["cause"]: v for v in verify_actions(df, LABEL)}
    proto_v = verify_actions(df, "cause_hat")
    base_v = {v["cause"]: v for v in verify_actions(df, "baseline_cause")}
    eff_truth = [c for c, m in ACTION_LIBRARY.items() if m["implemented"] and m["sim_effect"] >= VERIFY_MIN_REDUCTION]
    ineff = [c for c, m in ACTION_LIBRARY.items() if m["implemented"] and m["sim_effect"] < VERIFY_MIN_REDUCTION]
    pv = {v["cause"]: v for v in proto_v}
    for v in proto_v:
        v["true_effect_pct_assumed"] = round(100 * ACTION_LIBRARY[v["cause"]]["sim_effect"], 1)
        v["measured_minus_assumed_pp"] = round(v["reduction_pct"] - v["true_effect_pct_assumed"], 1)
        v["reduction_if_labels_were_perfect_pct"] = truth[v["cause"]]["reduction_pct"]
    verified = [v for v in proto_v if v["status"] == "VERIFIED"]
    R["corrective_actions"] = proto_v
    saved_h_day = sum(v["hidden_seconds_saved_per_day"] for v in verified) / 3600
    R["verification_benchmark"] = {
        "effective_actions": eff_truth, "ineffective_actions": ineff,
        "prototype_recall_of_effective": round(sum(pv[c]["status"] == "VERIFIED" for c in eff_truth) / len(eff_truth), 3),
        "baseline_recall_of_effective": round(sum(base_v[c]["status"] == "VERIFIED" for c in eff_truth) / len(eff_truth), 3),
        "ineffective_not_verified_prototype": round(float(np.mean([pv[c]["status"] != "VERIFIED" for c in ineff])), 3),
        "ineffective_not_verified_baseline": round(float(np.mean([base_v[c]["status"] != "VERIFIED" for c in ineff])), 3),
        "control_causes_falsely_would_verify": [c for c, m in ACTION_LIBRARY.items() if not m["implemented"] and c != "UNKNOWN" and pv[c]["stat_status_if_tested"] == "WOULD_VERIFY"],
        "verified_mean_reduction": round(float(np.mean([v["reduction_pct"] for v in verified])) / 100, 3) if verified else 0.0,
        "mean_abs_estimate_error_pp_effective": round(float(np.mean([abs(pv[c]["measured_minus_assumed_pp"]) for c in eff_truth])), 1),
        "baseline_mean_abs_estimate_error_pp_effective_and_ineffective": round(float(np.mean([abs(base_v[c]["reduction_pct"] - 100 * ACTION_LIBRARY[c]["sim_effect"]) for c in eff_truth + ineff])), 1),
        "prototype_mean_abs_estimate_error_pp_effective_and_ineffective": round(float(np.mean([abs(pv[c]["reduction_pct"] - 100 * ACTION_LIBRARY[c]["sim_effect"]) for c in eff_truth + ineff])), 1),
        "baseline_status": {c: base_v[c]["status"] for c in eff_truth + ineff},
        "baseline_reduction_pct": {c: base_v[c]["reduction_pct"] for c in eff_truth + ineff},
        "verified_hidden_hours_saved_per_day": round(saved_h_day, 3),
    }

    # ---- 8. patterns (deployed) and unknown clusters
    R["patterns"] = miner.mine_patterns(df, pd.DataFrame({"cause": df.cause_hat, "confidence": df.confidence}, index=df.index))
    R["unknown_clusters"] = miner.discover_unknown_clusters(test, pt)

    # ---- 9. cost / benefit (assumptions in config + docs)
    annual_h = saved_h_day * OPERATING_DAYS_PER_YEAR
    cost = {"build_hours": 120, "build_rate_usd": 30, "edge_pc_usd": 600, "maintenance_hours_per_month": 6, "corrective_action_hardware_usd": 4000}
    y1 = cost["build_hours"] * cost["build_rate_usd"] + cost["edge_pc_usd"] + cost["maintenance_hours_per_month"] * 12 * cost["build_rate_usd"] + cost["corrective_action_hardware_usd"]
    R["cost_benefit"] = {"assumptions": cost, "verified_hours_saved_per_year": round(annual_h, 1), "annual_benefit_usd": round(annual_h * COST_PER_STATION_HOUR_USD),
                         "year1_cost_usd": y1, "payback_months": round(12 * y1 / max(annual_h * COST_PER_STATION_HOUR_USD, 1), 1),
                         "annual_idle_kwh_avoided": round(annual_h * COBOT_IDLE_KW), "annual_co2_kg_avoided": round(annual_h * COBOT_IDLE_KW * GRID_KG_CO2_PER_KWH)}

    # ---- 10. targets
    vb, fsd = R["verification_benchmark"], max(f["proto_drop"] for f in fs)
    T = TARGETS
    R["targets"] = [
        {"metric": "Prototype macro-F1 (cause attribution)", "baseline": R["baseline"]["macro_f1"], "target": f">= {T['prototype_macro_f1']}", "measured": R["prototype"]["macro_f1"], "pass": R["prototype"]["macro_f1"] >= T["prototype_macro_f1"]},
        {"metric": "Macro-F1 gain over baseline", "baseline": 0.0, "target": f">= +{T['macro_f1_gain_over_baseline']}", "measured": round(R["prototype"]["macro_f1"] - R["baseline"]["macro_f1"], 4), "pass": R["prototype"]["macro_f1"] - R["baseline"]["macro_f1"] >= T["macro_f1_gain_over_baseline"]},
        {"metric": "Hidden downtime attributed to correct cause (share of seconds)", "baseline": R["hidden_downtime"]["baseline_correct_share"], "target": f">= {T['hidden_downtime_correct_share']}", "measured": R["hidden_downtime"]["prototype_correct_share"], "pass": R["hidden_downtime"]["prototype_correct_share"] >= T["hidden_downtime_correct_share"]},
        {"metric": "Top-4 cause downtime attribution error (%)", "baseline": R["downtime_attribution"]["baseline"]["top4_mean_error_pct"], "target": f"<= {T['top_cause_downtime_error_pct']}", "measured": R["downtime_attribution"]["prototype"]["top4_mean_error_pct"], "pass": R["downtime_attribution"]["prototype"]["top4_mean_error_pct"] <= T["top_cause_downtime_error_pct"]},
        {"metric": "Effective corrective actions correctly VERIFIED (recall)", "baseline": vb["baseline_recall_of_effective"], "target": f">= {T['action_verification_recall']}", "measured": vb["prototype_recall_of_effective"], "pass": vb["prototype_recall_of_effective"] >= T["action_verification_recall"]},
        {"metric": "Ineffective action NOT verified", "baseline": vb["ineffective_not_verified_baseline"], "target": f"= {T['ineffective_action_not_verified']}", "measured": vb["ineffective_not_verified_prototype"], "pass": vb["ineffective_not_verified_prototype"] >= T["ineffective_action_not_verified"]},
        {"metric": "Mean measured reduction of verified actions", "baseline": None, "target": f">= {T['verified_mean_reduction']}", "measured": vb["verified_mean_reduction"], "pass": vb["verified_mean_reduction"] >= T["verified_mean_reduction"]},
        {"metric": "Worst macro-F1 drop across failure states", "baseline": max(f["base_drop"] for f in fs), "target": f"<= {T['worst_failure_macro_f1_drop']}", "measured": round(fsd, 4), "pass": fsd <= T["worst_failure_macro_f1_drop"]},
        {"metric": "Unseen cause NOT confidently misattributed", "baseline": 0.0, "target": f">= {T['unseen_cause_abstain_rate']}", "measured": unseen["abstained_or_unknown_rate"], "pass": unseen["abstained_or_unknown_rate"] >= T["unseen_cause_abstain_rate"]},
    ]

    if save:
        REPORTS_DIR.mkdir(exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        json.dump(R, open(RESULTS_PATH, "w"), indent=2, default=str)
        df.drop(columns=["corrective_action"], errors="ignore").to_csv(PROCESSED_DIR / "events_scored.csv", index=False)
        joblib.dump(miner, PROCESSED_DIR / "miner.joblib")
        from src.evaluation.report import make_figures, write_reports
        make_figures(R, df); write_reports(R)
    return R


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: r[k] for k in ["baseline", "prototype", "ablation_macro_f1", "hidden_downtime"] if k != "hidden_downtime"}, indent=1))
    for t in r["targets"]:
        print(("PASS" if t["pass"] else "FAIL"), t["metric"], "| baseline", t["baseline"], "| target", t["target"], "| measured", t["measured"])
