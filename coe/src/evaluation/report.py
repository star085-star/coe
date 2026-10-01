"""Figures and markdown reports generated from results.json (numbers in docs always come from the run)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.utils.config import FIGURES_DIR, REPORTS_DIR, TARGETS, VERIFY_MIN_REDUCTION, VERIFY_ALPHA


def make_figures(R, df):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    labs = [l.replace("_", "\n") for l in R["confusion_matrix"]["labels"]]
    cm = np.array(R["confusion_matrix"]["matrix"]); cmn = cm / cm.sum(1, keepdims=True)
    fig, ax = plt.subplots(figsize=(9, 7.5)); im = ax.imshow(cmn, cmap="Blues")
    ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs, fontsize=6, rotation=45, ha="right"); ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs, fontsize=6)
    for i in range(len(labs)):
        for j in range(len(labs)):
            ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center", fontsize=6, color="white" if cmn[i, j] > .5 else "black")
    ax.set_xlabel("Predicted"); ax.set_ylabel("True (verified)"); ax.set_title("Prototype confusion matrix (row-normalised, held-out events)")
    fig.tight_layout(); fig.savefig(FIGURES_DIR / "confusion_matrix.png", dpi=130); plt.close(fig)

    le = R["label_efficiency"]; fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar([100 * r["labeled_fraction"] for r in le], [r["macro_f1_mean"] for r in le], [r["macro_f1_std"] for r in le], marker="o", capsize=3, label="Prototype")
    ax.axhline(R["baseline"]["macro_f1"], color="tab:red", ls="--", label="Rule baseline (no labels)")
    ax.set_xlabel("% of events with verified root-cause label"); ax.set_ylabel("Macro-F1"); ax.set_title("Label efficiency"); ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(FIGURES_DIR / "label_efficiency.png", dpi=130); plt.close(fig)

    fs = R["failure_states"]; x = np.arange(len(fs)); fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(x - .2, [f["base_macro_f1"] for f in fs], .4, label="Baseline", color="tab:red"); ax.bar(x + .2, [f["proto_macro_f1"] for f in fs], .4, label="Prototype", color="tab:blue")
    ax.axhline(R["prototype"]["macro_f1"], color="tab:blue", ls=":", lw=1)
    ax.set_xticks(x); ax.set_xticklabels([f["failure_state"].replace("_", "\n") for f in fs], fontsize=6.5); ax.set_ylabel("Macro-F1"); ax.set_title("Failure-state tests"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES_DIR / "failure_states.png", dpi=130); plt.close(fig)

    ca = [c for c in R["corrective_actions"] if c["implemented"]]; fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(ca)); ax.bar(x - .2, [c["rate_pre_per_h"] for c in ca], .4, label="Before action"); ax.bar(x + .2, [c["rate_post_per_h"] for c in ca], .4, label="After action")
    for i, c in enumerate(ca):
        ax.text(i, max(c["rate_pre_per_h"], c["rate_post_per_h"]) + .5, f"-{c['reduction_pct']}%\n{c['status']}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels([c["cause"].replace("_", "\n") for c in ca], fontsize=6.5); ax.set_ylabel("Stoppages per operating hour"); ax.set_title("Corrective-action verification (pre vs post)")
    ax.set_ylim(0, max(c["rate_pre_per_h"] for c in ca) * 1.3); ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES_DIR / "corrective_actions.png", dpi=130); plt.close(fig)


def _tbl(rows, header):
    s = "| " + " | ".join(header) + " |\n|" + "|".join("---" for _ in header) + "|\n"
    return s + "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows) + "\n"


def write_reports(R):
    vb, hd, ea = R["verification_benchmark"], R["hidden_downtime"], R["error_analysis"]
    n_pass = sum(t["pass"] for t in R["targets"])
    tgt = _tbl([[t["metric"], t["baseline"], t["target"], t["measured"], "PASS" if t["pass"] else "**FAIL**"] for t in R["targets"]], ["Metric", "Baseline", "Target (set before run)", "Measured", "Result"])
    fs = _tbl([[f["failure_state"], f["base_macro_f1"], f["proto_macro_f1"], f"-{f['proto_drop']:.3f}"] for f in R["failure_states"]], ["Failure state", "Baseline macro-F1", "Prototype macro-F1", "Prototype drop"])
    ca = _tbl([[c["cause"], c["action_id"], c["n_pre"], c["n_post"], c["rate_pre_per_h"], c["rate_post_per_h"], f"{c['reduction_pct']}% {c['reduction_ci95_pct']}", f"{c['p_value']:.1e}", c["status"], f"{c['true_effect_pct_assumed']}%"] for c in R["corrective_actions"]],
              ["Cause", "Action", "n pre", "n post", "rate/h pre", "rate/h post", "Reduction (95% CI)", "p", "Status", "Assumed true effect"])
    pc = _tbl([[p["cause"], p["support"] if "support" in p else "", p["proto_precision"], p["proto_recall"], p["proto_f1"], p["base_f1"]] for p in R["per_cause"]], ["Cause", "Support", "Precision", "Recall", "Prototype F1", "Baseline F1"])
    ms = json.load(open(REPORTS_DIR / "multi_seed_results.json"))["summary"] if (REPORTS_DIR / "multi_seed_results.json").exists() else None
    gt = hd["ground_truth_summary"]; cb = R["cost_benefit"]
    ev = f"""# Evaluation Report (auto-generated by `python -m src.evaluation.evaluate`)

**Data:** synthetic, {R['n_events']} cleaned events ({R['n_pre']} before / {R['n_post']} after corrective actions went live).
**Protocol:** only {R['n_labeled_train']} events (30%) carry a maintenance-verified root cause and are used for training; every number below on
classification is measured on the other {R['n_test']} held-out events. Targets were fixed before the first run.

## 1. Headline: {n_pass}/{len(R['targets'])} targets met
{tgt}
Two targets fail and are discussed honestly in section 5 and `error_analysis.md`.

## 2. Baseline vs prototype
Baseline = rule lookup on machine_state (+ product for WAITING_FOR_OPERATOR), which is what a plant can build from the MES alone.
Prototype = logistic regression on machine states + product + shift + station + duration + multilingual operator notes.

| | Accuracy | Macro-F1 |
|---|---|---|
| Baseline | {R['baseline']['accuracy']} | {R['baseline']['macro_f1']} |
| Prototype | {R['prototype']['accuracy']} | {R['prototype']['macro_f1']} |

Top-2 accuracy of the prototype: {R['prototype']['top2_accuracy']}; abstention rate: {R['prototype']['abstain_rate']}.

Ablation (macro-F1): structured only {R['ablation_macro_f1']['structured_only']}, text only {R['ablation_macro_f1']['text_only']}, both {R['ablation_macro_f1']['structured_plus_text']}.
Each signal alone is clearly weaker; the combination is what makes the stoppage causes visible.

![confusion](figures/confusion_matrix.png)

### Per-cause results
{pc}
### Label efficiency
![le](figures/label_efficiency.png)

{_tbl([[f"{100*r['labeled_fraction']:.0f}%", r['macro_f1_mean'], r['macro_f1_std']] for r in R['label_efficiency']], ['Labeled events', 'Macro-F1 (mean of 3 seeds)', 'Std'])}
## 3. Hidden downtime -> verified corrective actions
Hidden downtime = downtime the MES logged only as `UNCLASSIFIED_MICROSTOP`. In the ground truth that is **{gt['hidden_events']} events / {gt['hidden_hours']} h = {gt['hidden_share_of_all_downtime_pct']}%** of all stoppage time over {gt['span_days']} days.
Share of hidden-downtime seconds attributed to the correct cause (held-out events): prototype **{hd['prototype_correct_share']}** vs baseline **{hd['baseline_correct_share']}**.
Downtime attribution error for the top-4 causes: prototype {R['downtime_attribution']['prototype']['top4_mean_error_pct']}% vs baseline {R['downtime_attribution']['baseline']['top4_mean_error_pct']}%.

Verification rule: events per operating hour before vs after go-live; exact one-sided binomial rate test, Bonferroni-corrected over 8 causes (alpha {VERIFY_ALPHA}/8);
VERIFIED needs reduction >= {int(100*VERIFY_MIN_REDUCTION)}%.

{ca}
![ca](figures/corrective_actions.png)

* Effective actions correctly VERIFIED: prototype {vb['prototype_recall_of_effective']}, baseline {vb['baseline_recall_of_effective']}. **Pass/fail verification alone does not separate the two.**
* The deliberately ineffective action ({', '.join(vb['ineffective_actions'])}) was not verified by the prototype ({vb['ineffective_not_verified_prototype']}); the baseline's noisy causes reported a {vb['baseline_reduction_pct']['ROBOT_RECOVERY']}% reduction for it, leaving it INCONCLUSIVE instead of rejected.
* What does separate them is estimate accuracy: mean absolute error vs the simulated true effect is **{vb['prototype_mean_abs_estimate_error_pp_effective_and_ineffective']} pp (prototype) vs {vb['baseline_mean_abs_estimate_error_pp_effective_and_ineffective']} pp (baseline)**.
* Verified actions recover about {vb['verified_hidden_hours_saved_per_day']} stoppage-hours per day.
* Important caveat: the "assumed true effect" is chosen by the synthetic generator. The experiment shows the pipeline recovers known effects; it does **not** show that real actions work that well.

## 4. Failure states
{fs}
![fs](figures/failure_states.png)

Unseen cause test (cause `{R['unseen_cause']['held_out_cause']}` removed from training): only {R['unseen_cause']['abstained_or_unknown_rate']} of its events were routed to UNKNOWN; {R['unseen_cause']['misattributed_to_recurring_cause_rate']} were confidently attributed to a wrong known cause.

## 5. What did not work / iteration log
1. **Run 1** (no augmentation, no multiple-testing correction): macro-F1 0.905; worst failure drop 0.165; duration drift x3 cost 0.159; MATERIAL_SHORTAGE (no action implemented) would have been falsely VERIFIED by chance (30.7% reduction on ~200 events).
2. **Changes made after seeing run 1** (disclosed so the numbers are not read as pre-registered): (a) training-time augmentation (blank notes, dropped status flags, duration jitter); (b) Bonferroni correction for the verification test. Effect: duration-drift drop 0.159 -> {next(f['proto_drop'] for f in R['failure_states'] if f['failure_state']=='duration_drift_x3')}; false verification removed. Macro-F1 moved 0.905 -> {R['prototype']['macro_f1']}.
3. **Still failing:** (a) when notes AND flags are both lost the prototype loses ~{max(f['proto_drop'] for f in R['failure_states']):.2f} macro-F1; this is information-limited (structured-only ablation = {R['ablation_macro_f1']['structured_only']}) so the dashboard shows lower confidence and routes to review rather than hiding it. (b) A confidence threshold does **not** catch a genuinely new cause. Mitigation is procedural: weekly review of the lowest-margin events and the discovered-cluster list, plus human sign-off before any action is marked verified.

## 6. Robustness across datasets
""" + (f"5 freshly generated datasets (seeds 1-5, `scripts/multi_seed.py`): prototype macro-F1 mean {ms['prototype_macro_f1']['mean']} (range {ms['prototype_macro_f1']['min']}-{ms['prototype_macro_f1']['max']}) vs baseline {ms['baseline_macro_f1']['mean']}; hidden-downtime correct share {ms['hidden_correct_share']['mean']}; false verifications {ms['false_verifications']['max']} in every seed; estimate error {ms['est_error_pp_proto']['mean']} pp vs {ms['est_error_pp_base']['mean']} pp baseline; worst failure drop mean {ms['worst_drop']['mean']} (max {ms['worst_drop']['max']}, so the <= {TARGETS['worst_failure_macro_f1_drop']} target fails in every seed); unseen-cause abstention mean {ms['unseen_abstain']['mean']}.\n" if ms else "Run `python scripts/multi_seed.py` to add multi-seed results.\n") + f"""
## 7. Cost vs benefit (assumptions in `reports/cost_benefit_analysis.md`)
Year-1 cost ~${cb['year1_cost_usd']:,}; verified recovery ~{cb['verified_hours_saved_per_year']} h/yr ~ ${cb['annual_benefit_usd']:,}/yr; payback ~{cb['payback_months']} months. Idle energy avoided ~{cb['annual_idle_kwh_avoided']} kWh (~{cb['annual_co2_kg_avoided']} kg CO2): negligible, so the benefit is mainly throughput and operator relief. Dollar figures rest on assumed cost per station-hour and are illustrative.

## 8. Limitations
Synthetic data (generator rules and effect sizes are mine); real notes will be messier; no real operator validation yet; one plant; Tamil/Tanglish lexicon needs native-speaker review.
"""
    (REPORTS_DIR / "evaluation_report.md").write_text(ev)

    err = f"""# Error Analysis (auto-generated)

## Where the prototype is wrong
Top confusions (held-out events): {_tbl([[c['true'], c['predicted'], c['count']] for c in ea['top_confusions']], ['True', 'Predicted', 'Count'])}
The confused pairs share the WAITING / IDLE / BLOCKED family of machine states and similar "waiting" wording in notes, i.e. exactly the causes a human also finds hard to separate from the log alone.

## Language of the operator note
{_tbl([[k, v['n'], v['accuracy']] for k, v in ea['accuracy_by_note_language'].items()], ['Note language', 'Events', 'Accuracy'])}
Notes in Tamil script and Tanglish are not penalised (character n-grams + concept lexicon), but this is on synthetic phrases written for the generator; real free text will be harder. Events with **no note** are the weakest group.

## Misleading machine state
Accuracy when the logged state is the typical one for that cause: {ea['accuracy_when_machine_state_matches_typical']}; when the state is misleading: **{ea['accuracy_when_machine_state_is_misleading']}** (baseline: {ea['baseline_accuracy_when_state_misleading']}).
This is the core reason the baseline fails: it trusts machine_state alone.

## Confidence is informative
Mean confidence when correct {ea['mean_confidence_correct']} vs when wrong {ea['mean_confidence_wrong']} -> low-confidence events can be queued for human review.

## Highest-confidence mistakes (with the features that drove the prediction)
{chr(10).join(f"* `{e['event_id']}` true **{e['true']}**, predicted **{e['predicted']}** (conf {e['confidence']}); state={e['state']}; note=\"{e['note']}\"; drivers: {e['why']}" for e in ea['example_errors'])}

## Estimator error in action verification
{_tbl([[c['cause'], c['true_effect_pct_assumed'], c['reduction_pct'], c['reduction_if_labels_were_perfect_pct'], c['measured_minus_assumed_pp']] for c in R['corrective_actions'] if c['implemented']], ['Cause', 'Assumed true effect %', 'Measured % (deployed labels)', 'Measured % (perfect labels)', 'Error pp'])}
Errors come from (a) sampling noise in counts, (b) label noise that dilutes or shifts events between causes. The intervals are exact binomial; they cover the assumed effect in most rows but are not guaranteed to for the effect of an action on a mislabelled neighbour cause.

## Unseen cause and unknown clusters
Unseen-cause abstention was {R['unseen_cause']['abstained_or_unknown_rate']} (target {TARGETS['unseen_cause_abstain_rate']}): failed. Clusters formed from abstained events (for human review): {json.dumps(R['unknown_clusters'][:2])}
"""
    (REPORTS_DIR / "error_analysis.md").write_text(err)
