"""Repeat the whole experiment on freshly generated datasets (different seeds) to show variability."""
import json, sys, tempfile
from pathlib import Path
import numpy as np
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.data.generate_dataset import generate_synthetic_dataset
from src.data.preprocess import preprocess_dataset
from src.evaluation.evaluate import run
from src.utils.config import REPORTS_DIR

rows = []
for seed in range(1, 6):
    with tempfile.TemporaryDirectory() as tmp:
        raw, proc = Path(tmp) / "r.csv", Path(tmp) / "p.csv"
        generate_synthetic_dataset(seed=seed, output_path=raw)
        df = preprocess_dataset(raw, proc, sample_path=None, verbose=False)
    R = run(df, seed=seed, save=False)
    vb = R["verification_benchmark"]
    rows.append({"seed": seed, "baseline_macro_f1": R["baseline"]["macro_f1"], "prototype_macro_f1": R["prototype"]["macro_f1"],
                 "hidden_correct_share": R["hidden_downtime"]["prototype_correct_share"], "verif_recall": vb["prototype_recall_of_effective"],
                 "ineffective_not_verified": vb["ineffective_not_verified_prototype"], "false_verifications": len(vb["control_causes_falsely_would_verify"]),
                 "est_error_pp_proto": vb["prototype_mean_abs_estimate_error_pp_effective_and_ineffective"], "est_error_pp_base": vb["baseline_mean_abs_estimate_error_pp_effective_and_ineffective"],
                 "worst_drop": max(f["proto_drop"] for f in R["failure_states"]), "unseen_abstain": R["unseen_cause"]["abstained_or_unknown_rate"]})
    print(rows[-1], flush=True)
summary = {k: {"mean": round(float(np.mean([r[k] for r in rows])), 3), "min": round(float(np.min([r[k] for r in rows])), 3), "max": round(float(np.max([r[k] for r in rows])), 3)} for k in rows[0] if k != "seed"}
json.dump({"per_seed": rows, "summary": summary}, open(REPORTS_DIR / "multi_seed_results.json", "w"), indent=2)
print(json.dumps(summary, indent=1))
