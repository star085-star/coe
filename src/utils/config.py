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
