import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to python path if executing standalone
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.utils.config import (
    RAW_DATA_PATH,
    RANDOM_SEED,
    SHIFTS,
    WORKSTATIONS,
    COBOTS,
    PRODUCTS,
    PRODUCT_VARIANTS,
    MACHINE_STATES,
    ROBOT_MODES,
    VERIFIED_ROOT_CAUSES,
)

def set_seed(seed=RANDOM_SEED):
    random.seed(seed)
    np.random.seed(seed)

def generate_synthetic_dataset(num_records=10500):
    """
    Generates a realistic synthetic manufacturing dataset of micro-stoppage events with injected recurring patterns,
    multilingual operator notes (English, Tamil, Tanglish), noise, missing values, and specific edge cases.
    """
    set_seed(RANDOM_SEED)

    start_date = datetime(2026, 8, 1, 6, 0, 0)
    records = []

    # Text notes templates per pattern
    notes_dict = {
        "MATERIAL_MISALIGNMENT": [
            "material alignment issue on fixture",
            "part misaligned during load",
            "repositioning component manually",
            "material sariyaa align aagala",
            "material konjam shift aayiduchu",
            "fixture pin loose, part alignment bad",
            "load misalignment, reset part",
            "part seating error on tray",
            "operator repositioned stock",
            "konjam align maathi vekkanum"
        ],
        "SENSOR_INTERRUPTION": [
            "sensor blocked by dust",
            "optical sensor trip reset",
            "sensor block aachu",
            "sensor clean panninom",
            "presence sensor false trigger",
            "photoeye interrupted",
            "sensor misalignment detected",
            "sensor status degraded check lens",
            "dust clean pannadhum reset aachu",
            "proximity sensor delay"
        ],
        "OPERATOR_LOADING_DELAY": [
            "operator loading late",
            "material buffer empty waiting for operator",
            "operator occupied at adjacent station",
            "material edukka late aachu",
            "operator loading delay night shift",
            "manual loading cycle lag",
            "operator wait pannitu irundhuchu",
            "trolley swap delay by operator",
            "operator late on line",
            "part placement delay"
        ],
        "SAFETY_ZONE_INTERRUPTION": [
            "operator entered safety zone",
            "safety curtain breach",
            "warning zone slowdown trip",
            "zone breach aachu reset button pressed",
            "safety stop triggered by proximity",
            "collaborative zone slowdown",
            "safety perimeter sensor trip",
            "operator step into yellow zone",
            "safety stop trip clear",
            "safety zone breach"
        ],
        "ROBOT_RECOVERY": [
            "robot joint overload stop",
            "robot stopped reset required",
            "robot stop aachu reset panninom",
            "gripper fault recovery sequence",
            "cobot axis 3 torque limit exceeded",
            "robot recovery routine executed",
            "cobot reset after trajectory hold",
            "robot hang aayiduchu restart பண்ணினோம்",
            "cobot path clear and reset",
            "robot error state recovery"
        ],
        "TOOL_CHANGE": [
            "end effector tool change",
            "gripper jaw replacement",
            "tool change panninom",
            "scheduled tool wear check",
            "tool swapper manual intervention"
        ],
        "QUALITY_INSPECTION_DELAY": [
            "checking dimension variance",
            "quality verification wait",
            "check pannitu irundhom gauge fault",
            "quality hold on batch sample",
            "marginal inspection re-measurement"
        ],
        "MATERIAL_SHORTAGE": [
            "stock empty on feeder",
            "trolley late material shortage",
            "stock illa waiting for bin refill",
            "feeder empty waiting AGV",
            "raw material bin depleted"
        ],
        "UNKNOWN": [
            "minor pause",
            "brief check",
            "konjam rest",
            "normal check",
            "system pause",
            "random delay",
            "no clear issue",
            "test run"
        ]
    }

    corrective_actions_dict = {
        "MATERIAL_MISALIGNMENT": "Review loading fixture alignment and add operator visual guide.",
        "SENSOR_INTERRUPTION": "Install protective lens cover and recalibrate optical sensor.",
        "OPERATOR_LOADING_DELAY": "Implement visual queue system and adjust material delivery cadence.",
        "SAFETY_ZONE_INTERRUPTION": "Optimize cobot speed trajectory near operator workspace boundaries.",
        "ROBOT_RECOVERY": "Update motion trajectory payload limits and perform joint torque calibration.",
        "TOOL_CHANGE": "Standardize quick-change tooling procedure.",
        "QUALITY_INSPECTION_DELAY": "Automate inline vision-based quality verification.",
        "MATERIAL_SHORTAGE": "Integrate AGV auto-replenishment trigger at low stock threshold.",
        "UNKNOWN": "Log operational event for further observation."
    }

    # Weight distribution for patterns to create clear dominant recurring causes
    causes = [
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
    cause_weights = [0.28, 0.22, 0.18, 0.12, 0.10, 0.04, 0.03, 0.02, 0.01]

    curr_time = start_date

    for i in range(1, num_records + 1):
        event_id = f"EVT_{i:06d}"
        
        # Advance timestamp realistically (10s to 120s between micro-stoppages)
        curr_time += timedelta(seconds=random.randint(15, 180))
        
        hour = curr_time.hour
        if 6 <= hour < 14:
            shift = "Shift_1"
        elif 14 <= hour < 22:
            shift = "Shift_2"
        else:
            shift = "Shift_3"

        # Select cause based on injected patterns
        cause = random.choices(causes, weights=cause_weights)[0]

        # Enforce realistic feature correlations based on patterns
        if cause == "MATERIAL_MISALIGNMENT":
            product = random.choices(["Product_A", "Product_B", "Product_C"], weights=[0.75, 0.15, 0.10])[0]
            eff_shift = random.choices(["Shift_2", "Shift_1", "Shift_3"], weights=[0.65, 0.25, 0.10])[0]
            workstation = random.choices(["WS_01", "WS_02", "WS_03"], weights=[0.60, 0.30, 0.10])[0]
            machine_state = "WAITING_FOR_OPERATOR"
            prev_state = "RUNNING"
            next_state = random.choice(["RECOVERY", "RUNNING"])
            duration = round(random.uniform(20.0, 60.0), 1)
            robot_mode = "COLLABORATIVE"
            safety_status = "CLEAR"
            sensor_status = random.choice(["OK", "MISALIGNED"])
            material_status = "MISALIGNED"
            quality_status = "PASS"

        elif cause == "SENSOR_INTERRUPTION":
            product = random.choice(PRODUCTS)
            eff_shift = shift
            workstation = random.choice(WORKSTATIONS[:5])
            machine_state = random.choice(["ERROR", "BLOCKED"])
            prev_state = "RUNNING"
            next_state = "RUNNING"
            duration = round(random.uniform(5.0, 25.0), 1)
            robot_mode = "AUTOMATIC"
            safety_status = "CLEAR"
            sensor_status = random.choice(["BLOCKED", "DEGRADED", "MISALIGNED"])
            material_status = "PRESENT"
            quality_status = "PASS"

        elif cause == "OPERATOR_LOADING_DELAY":
            product = random.choice(PRODUCTS)
            eff_shift = random.choices(["Shift_3", "Shift_2", "Shift_1"], weights=[0.65, 0.25, 0.10])[0]
            workstation = random.choice(WORKSTATIONS)
            machine_state = "WAITING_FOR_OPERATOR"
            prev_state = "RUNNING"
            next_state = "RUNNING"
            duration = round(random.uniform(30.0, 90.0), 1)
            robot_mode = "COLLABORATIVE"
            safety_status = "CLEAR"
            sensor_status = "OK"
            material_status = random.choice(["PRESENT", "EMPTY"])
            quality_status = "PASS"

        elif cause == "SAFETY_ZONE_INTERRUPTION":
            product = random.choice(PRODUCTS)
            eff_shift = shift
            workstation = random.choice(WORKSTATIONS)
            machine_state = "SAFETY_STOP"
            prev_state = "RUNNING"
            next_state = "RECOVERY"
            duration = round(random.uniform(10.0, 40.0), 1)
            robot_mode = "COLLABORATIVE"
            safety_status = random.choice(["BREACHED", "WARNING_ZONE"])
            sensor_status = "OK"
            material_status = "PRESENT"
            quality_status = "PASS"

        elif cause == "ROBOT_RECOVERY":
            product = random.choice(PRODUCTS)
            eff_shift = shift
            workstation = random.choice(WORKSTATIONS)
            machine_state = "RECOVERY"
            prev_state = "ERROR"
            next_state = "RUNNING"
            duration = round(random.uniform(20.0, 120.0), 1)
            robot_mode = random.choice(["MANUAL_RECOVERY", "ESTOP"])
            safety_status = "CLEAR"
            sensor_status = "OK"
            material_status = "PRESENT"
            quality_status = "PASS"

        elif cause == "TOOL_CHANGE":
            product = random.choice(PRODUCTS)
            eff_shift = shift
            workstation = random.choice(WORKSTATIONS)
            machine_state = "TOOL_CHANGE"
            prev_state = "RUNNING"
            next_state = "RUNNING"
            duration = round(random.uniform(40.0, 150.0), 1)
            robot_mode = "TEACH_MODE"
            safety_status = "MUTED"
            sensor_status = "OK"
            material_status = "PRESENT"
            quality_status = "PASS"

        elif cause == "QUALITY_INSPECTION_DELAY":
            product = random.choice(["Product_C", "Product_D"])
            eff_shift = shift
            workstation = random.choice(WORKSTATIONS)
            machine_state = "INSPECTION_HOLD"
            prev_state = "RUNNING"
            next_state = "RUNNING"
            duration = round(random.uniform(25.0, 100.0), 1)
            robot_mode = "COLLABORATIVE"
            safety_status = "CLEAR"
            sensor_status = "OK"
            material_status = "PRESENT"
            quality_status = random.choice(["INSPECTION_PENDING", "MARGINAL"])

        elif cause == "MATERIAL_SHORTAGE":
            product = random.choice(PRODUCTS)
            eff_shift = shift
            workstation = random.choice(WORKSTATIONS)
            machine_state = "IDLE"
            prev_state = "RUNNING"
            next_state = "RUNNING"
            duration = round(random.uniform(60.0, 240.0), 1)
            robot_mode = "AUTOMATIC"
            safety_status = "CLEAR"
            sensor_status = "OK"
            material_status = "EMPTY"
            quality_status = "PASS"

        else: # UNKNOWN
            product = random.choice(PRODUCTS)
            eff_shift = shift
            workstation = random.choice(WORKSTATIONS)
            machine_state = random.choice(MACHINE_STATES)
            prev_state = "RUNNING"
            next_state = "RUNNING"
            duration = round(random.uniform(2.0, 30.0), 1)
            robot_mode = random.choice(ROBOT_MODES)
            safety_status = "CLEAR"
            sensor_status = "OK"
            material_status = "PRESENT"
            quality_status = "PASS"

        # Cobot & Operator mapping
        cobot_id = f"COBOT_{int(workstation.split('_')[1]):02d}"
        operator_id = f"OP_{random.randint(101, 125):03d}"
        variant = random.choice(PRODUCT_VARIANTS)
        batch = f"BATCH_{curr_time.strftime('%Y%m%d')}_{random.randint(1, 5):02d}"
        temp = round(random.uniform(21.5, 34.0), 1)
        cycle_time = round(random.uniform(45.0, 110.0), 1)

        # Note selection with noise & missing notes
        if random.random() < 0.08:  # 8% missing notes
            note = ""
        else:
            note = random.choice(notes_dict[cause])

        # Verification Status simulation
        # ~60% of major patterns are VERIFIED or IMPLEMENTED
        verif_status = random.choices(
            ["VERIFIED", "IMPLEMENTED", "PENDING", "REJECTED"],
            weights=[0.45, 0.25, 0.20, 0.10]
        )[0]
        corrective_action = corrective_actions_dict[cause]

        rec = {
            "event_id": event_id,
            "timestamp": curr_time.strftime("%Y-%m-%d %H:%M:%S"),
            "workstation_id": workstation,
            "cobot_id": cobot_id,
            "machine_state": machine_state,
            "previous_machine_state": prev_state,
            "next_machine_state": next_state,
            "operator_id": operator_id,
            "operator_note": note,
            "product": product,
            "product_variant": variant,
            "shift": eff_shift,
            "stoppage_duration_seconds": duration,
            "robot_mode": robot_mode,
            "safety_zone_status": safety_status,
            "sensor_status": sensor_status,
            "material_status": material_status,
            "quality_status": quality_status,
            "temperature": temp,
            "cycle_time_seconds": cycle_time,
            "production_batch": batch,
            "verified_root_cause": cause,
            "corrective_action": corrective_action,
            "verification_status": verif_status
        }
        records.append(rec)

    df = pd.DataFrame(records)

    # Inject specific synthetic flaws & edge cases for testing pipeline robustness
    # Edge case 1: Unknown machine state
    df.loc[12, "machine_state"] = "UNKNOWN_ERR_STATE"
    # Edge case 2: Impossible negative duration
    df.loc[45, "stoppage_duration_seconds"] = -15.0
    # Edge case 3: Very short 1.0 second duration
    df.loc[78, "stoppage_duration_seconds"] = 1.0
    # Edge case 4: Duplicate event_id
    df.loc[100, "event_id"] = df.loc[99, "event_id"]

    # Save to data/raw/micro_stoppages_raw.csv
    RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"Generated {len(df)} records saved to {RAW_DATA_PATH}")
    return df

if __name__ == "__main__":
    generate_synthetic_dataset()
