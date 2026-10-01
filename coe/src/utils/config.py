import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "micro_stoppages_raw.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "micro_stoppages_processed.csv"
SAMPLE_DATA_PATH = DATA_DIR / "sample" / "micro_stoppages_sample.csv"
REPORTS_DIR = BASE_DIR / "reports"

# Random Seed for Reproducibility
RANDOM_SEED = 42

# Domain Categories
SHIFTS = ["Shift_1", "Shift_2", "Shift_3"]
WORKSTATIONS = [f"WS_{i:02d}" for i in range(1, 11)]
COBOTS = [f"COBOT_{i:02d}" for i in range(1, 11)]
PRODUCTS = ["Product_A", "Product_B", "Product_C", "Product_D"]
PRODUCT_VARIANTS = ["Std", "Pro", "Lite", "Max"]

MACHINE_STATES = [
    "RUNNING",
    "WAITING_FOR_OPERATOR",
    "ERROR",
    "RECOVERY",
    "SAFETY_STOP",
    "TOOL_CHANGE",
    "INSPECTION_HOLD",
    "BLOCKED",
    "IDLE"
]

ROBOT_MODES = ["AUTOMATIC", "COLLABORATIVE", "MANUAL_RECOVERY", "TEACH_MODE", "ESTOP"]
SAFETY_ZONE_STATUSES = ["CLEAR", "WARNING_ZONE", "BREACHED", "MUTED"]
SENSOR_STATUSES = ["OK", "BLOCKED", "MISALIGNED", "DEGRADED", "DISCONNECTED"]
MATERIAL_STATUSES = ["PRESENT", "MISALIGNED", "JAMMED", "EMPTY", "DAMAGED"]
QUALITY_STATUSES = ["PASS", "MARGINAL", "INSPECTION_PENDING", "REJECT"]

VERIFIED_ROOT_CAUSES = [
    "MATERIAL_MISALIGNMENT",
    "SENSOR_INTERRUPTION",
    "OPERATOR_LOADING_DELAY",
    "SAFETY_ZONE_INTERRUPTION",
    "ROBOT_RECOVERY",
    "TOOL_CHANGE",
    "QUALITY_INSPECTION_DELAY",
    "MATERIAL_SHORTAGE",
    "UNKNOWN"
]


# ---------------------------------------------------------------------------
# Phase 2 additions
# ---------------------------------------------------------------------------
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_PATH = REPORTS_DIR / "results.json"
FIGURES_DIR = REPORTS_DIR / "figures"
SIGNOFF_PATH = PROCESSED_DIR / "action_signoffs.json"

# Confidence below which the miner abstains (routes event to human review / UNKNOWN)
ABSTAIN_THRESHOLD = 0.35
# Fraction of events that carry a maintenance-verified root-cause label (realistic: labels are scarce)
LABELED_FRACTION = 0.30

# Timeline of the simulated intervention experiment
SIM_START = "2026-08-01 06:00:00"
POST_START = "2026-08-08 06:00:00"   # corrective actions go live here

# MES reason codes. Micro-stoppages are "recorded as downtime" but only two causes
# are auto-coded by the controller; everything else is hidden under a generic code.
GENERIC_MES_CODE = "UNCLASSIFIED_MICROSTOP"

# Corrective-action library. `sim_effect` is the ASSUMED true reduction used only by the
# synthetic generator (ground truth for judging the estimator). The pipeline never reads it.
ACTION_LIBRARY = {
    "MATERIAL_MISALIGNMENT": {"action_id": "CA-01", "text": "Re-machine loading fixture locating pins and add poka-yoke visual guide.", "implemented": True, "sim_effect": 0.65},
    "SENSOR_INTERRUPTION": {"action_id": "CA-02", "text": "Fit protective lens cover, add weekly lens-cleaning checklist, recalibrate optical sensor.", "implemented": True, "sim_effect": 0.70},
    "OPERATOR_LOADING_DELAY": {"action_id": "CA-03", "text": "Rebalance material delivery cadence and add visual replenishment (kanban) signal on night shift.", "implemented": True, "sim_effect": 0.45},
    "SAFETY_ZONE_INTERRUPTION": {"action_id": "CA-04", "text": "Tune cobot speed-and-separation zones; mark operator standing area on floor.", "implemented": True, "sim_effect": 0.35},
    "ROBOT_RECOVERY": {"action_id": "CA-05", "text": "Re-teach trajectory and recalibrate joint torque limits.", "implemented": True, "sim_effect": 0.03},  # deliberately ineffective
    "TOOL_CHANGE": {"action_id": "CA-06", "text": "Standardise quick-change tooling procedure.", "implemented": False, "sim_effect": 0.0},
    "QUALITY_INSPECTION_DELAY": {"action_id": "CA-07", "text": "Add inline vision check to replace manual gauge hold.", "implemented": False, "sim_effect": 0.0},
    "MATERIAL_SHORTAGE": {"action_id": "CA-08", "text": "Add low-stock trigger for AGV replenishment.", "implemented": False, "sim_effect": 0.0},
    "UNKNOWN": {"action_id": "CA-00", "text": "No recurring pattern: keep observing.", "implemented": False, "sim_effect": 0.0},
}

# Verification rule for corrective actions (rate of stoppages per operating hour, pre vs post)
VERIFY_MIN_REDUCTION = 0.30
VERIFY_ALPHA = 0.01
REJECT_ALPHA = 0.05
REJECT_MAX_REDUCTION = 0.10

# Cost model assumptions (see reports/cost_benefit_analysis.md). Edit to match the plant.
COST_PER_STATION_HOUR_USD = 60.0     # contribution margin lost per cobot-station hour of downtime
OPERATING_DAYS_PER_YEAR = 330
CELLS_IN_SCOPE = 10
COBOT_IDLE_KW = 0.25                 # assumed idle draw incl. controller
GRID_KG_CO2_PER_KWH = 0.71           # approximate India grid average; edit for your grid

# Success targets - fixed BEFORE running the experiment
TARGETS = {
    "prototype_macro_f1": 0.80,
    "macro_f1_gain_over_baseline": 0.10,
    "hidden_downtime_correct_share": 0.80,
    "top_cause_downtime_error_pct": 10.0,
    "action_verification_recall": 0.75,
    "ineffective_action_not_verified": 1.0,
    "verified_mean_reduction": 0.30,
    "worst_failure_macro_f1_drop": 0.15,
    "unseen_cause_abstain_rate": 0.50,
}
