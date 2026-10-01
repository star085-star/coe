"""Synthetic micro-stoppage generator for a human + cobot plant.

Design goals (why this is not a trivial lookup problem):
  * machine_state is only a NOISY hint of the cause (30% of events log a confusable state)
  * status flags (sensor/material/safety) drop out 25% of the time
  * notes are English / Tanglish / Tamil script; 10% missing, 14% generic, 4% misleading, 10% typos
  * shift is derived from the timestamp; causes are more likely on certain shifts/stations/products
  * a PRE/POST experiment: at POST_START corrective actions go live and treated causes are thinned.
    One action (ROBOT_RECOVERY) is deliberately ineffective so verification can reject it.
The injected effect sizes live in config.ACTION_LIBRARY (sim_effect) and are ASSUMPTIONS.
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.utils.config import (RAW_DATA_PATH, RANDOM_SEED, WORKSTATIONS, PRODUCTS, PRODUCT_VARIANTS,
                              MACHINE_STATES, ROBOT_MODES, SENSOR_STATUSES, MATERIAL_STATUSES, SAFETY_ZONE_STATUSES,
                              QUALITY_STATUSES, SIM_START, POST_START, ACTION_LIBRARY,
                              GENERIC_MES_CODE)

NOTES = {
    "MATERIAL_MISALIGNMENT": ["material alignment issue on fixture", "part misaligned during load", "repositioning component manually",
        "material sariyaa align aagala", "material konjam shift aayiduchu", "fixture pin loose, part alignment bad", "load misalignment, reset part",
        "part seating error on tray", "operator repositioned stock", "konjam align maathi vekkanum", "பொருள் சரியாக அமரவில்லை", "பொருள் இடம் மாறியது"],
    "SENSOR_INTERRUPTION": ["sensor blocked by dust", "optical sensor trip reset", "sensor block aachu", "sensor clean panninom", "presence sensor false trigger",
        "photoeye interrupted", "sensor misalignment detected", "sensor status degraded check lens", "dust clean pannadhum reset aachu", "proximity sensor delay",
        "சென்சார் தூசி அடைப்பு", "சென்சார் தடை ஆனது"],
    "OPERATOR_LOADING_DELAY": ["operator loading late", "material buffer empty waiting for operator", "operator occupied at adjacent station", "material edukka late aachu",
        "operator loading delay night shift", "manual loading cycle lag", "operator wait pannitu irundhuchu", "trolley swap delay by operator", "operator late on line",
        "part placement delay", "ஆபரேட்டர் ஏற்ற தாமதம்", "ஏற்றுவதில் தாமதம்"],
    "SAFETY_ZONE_INTERRUPTION": ["operator entered safety zone", "safety curtain breach", "warning zone slowdown trip", "zone breach aachu reset button pressed",
        "safety stop triggered by proximity", "collaborative zone slowdown", "safety perimeter sensor trip", "operator step into yellow zone", "safety stop trip clear",
        "safety zone breach", "பாதுகாப்பு மண்டலம் மீறல்", "மண்டலத்தில் நுழைந்தார்"],
    "ROBOT_RECOVERY": ["robot joint overload stop", "robot stopped reset required", "robot stop aachu reset panninom", "gripper fault recovery sequence",
        "cobot axis 3 torque limit exceeded", "robot recovery routine executed", "cobot reset after trajectory hold", "robot hang aayiduchu restart panninom",
        "cobot path clear and reset", "robot error state recovery", "ரோபோ நின்றது மீட்டமைப்பு"],
    "TOOL_CHANGE": ["end effector tool change", "gripper jaw replacement", "tool change panninom", "scheduled tool wear check", "tool swapper manual intervention", "கருவி மாற்றம்"],
    "QUALITY_INSPECTION_DELAY": ["checking dimension variance", "quality verification wait", "check pannitu irundhom gauge fault", "quality hold on batch sample",
        "marginal inspection re-measurement", "தரம் சரிபார்ப்பு காத்திருப்பு"],
    "MATERIAL_SHORTAGE": ["stock empty on feeder", "trolley late material shortage", "stock illa waiting for bin refill", "feeder empty waiting AGV",
        "raw material bin depleted", "பொருள் இல்லை காத்திருப்பு"],
    "UNKNOWN": ["minor pause", "brief check", "konjam rest", "normal check", "system pause", "random delay", "no clear issue", "test run"],
}
GENERIC_NOTES = ["reset done", "ok now", "checked", "small stop", "restarted", "cleared", "nothing found", "resume", "seri aayiduchu", "சரி ஆனது"]

BASE_WEIGHT = {"MATERIAL_MISALIGNMENT": 0.28, "SENSOR_INTERRUPTION": 0.22, "OPERATOR_LOADING_DELAY": 0.18, "SAFETY_ZONE_INTERRUPTION": 0.12,
               "ROBOT_RECOVERY": 0.10, "TOOL_CHANGE": 0.04, "QUALITY_INSPECTION_DELAY": 0.03, "MATERIAL_SHORTAGE": 0.02, "UNKNOWN": 0.01}
SHIFT_FACTOR = {"MATERIAL_MISALIGNMENT": {"Shift_1": .6, "Shift_2": 1.8, "Shift_3": .6}, "OPERATOR_LOADING_DELAY": {"Shift_1": .4, "Shift_2": .8, "Shift_3": 2.2}}
# (state, prev, next, mode, safety, sensor, material, quality, duration range)
PROFILE = {
    "MATERIAL_MISALIGNMENT": ("WAITING_FOR_OPERATOR", "RUNNING", ("RECOVERY", "RUNNING"), "COLLABORATIVE", "CLEAR", "OK", "MISALIGNED", "PASS", (20, 60)),
    "SENSOR_INTERRUPTION": (("ERROR", "BLOCKED"), "RUNNING", ("RUNNING",), "AUTOMATIC", "CLEAR", ("BLOCKED", "DEGRADED", "MISALIGNED"), "PRESENT", "PASS", (5, 25)),
    "OPERATOR_LOADING_DELAY": ("WAITING_FOR_OPERATOR", "RUNNING", ("RUNNING",), "COLLABORATIVE", "CLEAR", "OK", ("PRESENT", "EMPTY"), "PASS", (30, 90)),
    "SAFETY_ZONE_INTERRUPTION": ("SAFETY_STOP", "RUNNING", ("RECOVERY",), "COLLABORATIVE", ("BREACHED", "WARNING_ZONE"), "OK", "PRESENT", "PASS", (10, 40)),
    "ROBOT_RECOVERY": ("RECOVERY", "ERROR", ("RUNNING",), ("MANUAL_RECOVERY", "ESTOP"), "CLEAR", "OK", "PRESENT", "PASS", (20, 120)),
    "TOOL_CHANGE": ("TOOL_CHANGE", "RUNNING", ("RUNNING",), "TEACH_MODE", "MUTED", "OK", "PRESENT", "PASS", (40, 150)),
    "QUALITY_INSPECTION_DELAY": ("INSPECTION_HOLD", "RUNNING", ("RUNNING",), "COLLABORATIVE", "CLEAR", "OK", "PRESENT", ("INSPECTION_PENDING", "MARGINAL"), (25, 100)),
    "MATERIAL_SHORTAGE": ("IDLE", "RUNNING", ("RUNNING",), "AUTOMATIC", "CLEAR", "OK", "EMPTY", "PASS", (60, 240)),
    "UNKNOWN": (tuple(MACHINE_STATES), "RUNNING", ("RUNNING",), tuple(ROBOT_MODES), "CLEAR", "OK", "PRESENT", "PASS", (2, 30)),
}
CONFUSABLE = {  # states that plausibly get logged for this cause instead of its "typical" one
    "MATERIAL_MISALIGNMENT": ["BLOCKED", "INSPECTION_HOLD", "ERROR", "IDLE"],
    "SENSOR_INTERRUPTION": ["WAITING_FOR_OPERATOR", "RECOVERY", "SAFETY_STOP", "IDLE"],
    "OPERATOR_LOADING_DELAY": ["IDLE", "BLOCKED", "INSPECTION_HOLD"],
    "SAFETY_ZONE_INTERRUPTION": ["RECOVERY", "ERROR", "WAITING_FOR_OPERATOR"],
    "ROBOT_RECOVERY": ["ERROR", "SAFETY_STOP", "BLOCKED", "WAITING_FOR_OPERATOR"],
    "TOOL_CHANGE": ["WAITING_FOR_OPERATOR", "RECOVERY", "IDLE"],
    "QUALITY_INSPECTION_DELAY": ["WAITING_FOR_OPERATOR", "BLOCKED", "IDLE"],
    "MATERIAL_SHORTAGE": ["WAITING_FOR_OPERATOR", "BLOCKED"],
    "UNKNOWN": MACHINE_STATES,
}
WS_BIAS = {"MATERIAL_MISALIGNMENT": (["WS_01", "WS_02", "WS_03"], [.6, .3, .1]), "SENSOR_INTERRUPTION": (WORKSTATIONS[:5], None)}
PROD_BIAS = {"MATERIAL_MISALIGNMENT": (["Product_A", "Product_B", "Product_C"], [.75, .15, .10]), "QUALITY_INSPECTION_DELAY": (["Product_C", "Product_D"], None)}


def _pick(x, rng):
    return rng.choice(x) if isinstance(x, (tuple, list)) else x


def _typo(text, rng):
    if len(text) < 6 or rng.random() > 0.10:
        return text
    i = rng.randrange(1, len(text) - 1)
    return text[:i] + text[i + 1:]


def _shift_of(ts):
    h = ts.hour
    return "Shift_1" if 6 <= h < 14 else "Shift_2" if 14 <= h < 22 else "Shift_3"


def generate_synthetic_dataset(num_records=10500, seed=RANDOM_SEED, save=True, output_path=RAW_DATA_PATH, inject_flaws=True):
    rng = random.Random(seed)
    nprng = np.random.default_rng(seed)
    t = datetime.strptime(SIM_START, "%Y-%m-%d %H:%M:%S")
    post = datetime.strptime(POST_START, "%Y-%m-%d %H:%M:%S")
    causes = list(BASE_WEIGHT)
    rows = []
    while len(rows) < num_records:
        t += timedelta(seconds=rng.randint(15, 180))
        shift = _shift_of(t)
        w = [BASE_WEIGHT[c] * SHIFT_FACTOR.get(c, {}).get(shift, 1.0) for c in causes]
        cause = rng.choices(causes, weights=w)[0]
        period = "POST" if t >= post else "PRE"
        if period == "POST" and rng.random() < ACTION_LIBRARY[cause]["sim_effect"]:
            continue  # the corrective action prevented this stoppage
        st, prev, nxt, mode, safety, sensor, material, quality, (lo, hi) = PROFILE[cause]
        state = _pick(st, rng)
        if rng.random() < 0.30:
            state = rng.choice(CONFUSABLE[cause])           # noisy machine_state
        # status flags: 25% drop out to defaults, and 25% carry an unrelated value (noisy PLC/sensor flags)
        sensor, material, safety, quality = _pick(sensor, rng), _pick(material, rng), _pick(safety, rng), _pick(quality, rng)
        if rng.random() < 0.25:
            sensor, material, safety, quality = "OK", "PRESENT", "CLEAR", "PASS"
        sensor = rng.choice(SENSOR_STATUSES) if rng.random() < 0.25 else sensor
        material = rng.choice(MATERIAL_STATUSES) if rng.random() < 0.25 else material
        safety = rng.choice(SAFETY_ZONE_STATUSES) if rng.random() < 0.20 else safety
        quality = rng.choice(QUALITY_STATUSES) if rng.random() < 0.20 else quality
        prev = rng.choice(MACHINE_STATES) if rng.random() < 0.40 else prev
        nxt_state = rng.choice(MACHINE_STATES) if rng.random() < 0.40 else _pick(nxt, rng)
        mode = _pick(mode, rng)
        mode = rng.choice(ROBOT_MODES) if rng.random() < 0.35 else mode
        if rng.random() < 0.10:
            state = rng.choice(MACHINE_STATES)          # completely wrong state log
        ws_opts, ws_w = WS_BIAS.get(cause, (WORKSTATIONS, None))
        ws = rng.choices(ws_opts, weights=ws_w)[0] if ws_w else rng.choice(ws_opts)
        pr_opts, pr_w = PROD_BIAS.get(cause, (PRODUCTS, None))
        product = rng.choices(pr_opts, weights=pr_w)[0] if pr_w else rng.choice(pr_opts)
        dur = float(np.clip(rng.uniform(lo, hi) * nprng.lognormal(0, 0.25), 2.0, 295.0))
        # operator note
        r = rng.random()
        if r < 0.10:
            note = ""
        elif r < 0.24:
            note = rng.choice(GENERIC_NOTES)
        elif r < 0.28:
            note = rng.choice(NOTES[rng.choice([c for c in causes if c != cause])])
        else:
            note = rng.choice(NOTES[cause])
        note = _typo(note, rng)
        act = ACTION_LIBRARY[cause]
        auto_coded = (cause == "SAFETY_ZONE_INTERRUPTION" and state == "SAFETY_STOP") or (cause == "TOOL_CHANGE" and state == "TOOL_CHANGE")
        rows.append({
            "event_id": f"EVT_{len(rows) + 1:06d}", "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"), "workstation_id": ws,
            "cobot_id": f"COBOT_{int(ws.split('_')[1]):02d}", "machine_state": state, "previous_machine_state": prev,
            "next_machine_state": nxt_state, "operator_id": f"OP_{rng.randint(101, 125):03d}", "operator_note": note,
            "product": product, "product_variant": rng.choice(PRODUCT_VARIANTS), "shift": shift,
            "stoppage_duration_seconds": round(dur, 1), "robot_mode": mode, "safety_zone_status": safety,
            "sensor_status": sensor, "material_status": material, "quality_status": quality,
            "temperature": round(rng.uniform(21.5, 34.0), 1), "cycle_time_seconds": round(rng.uniform(45, 110), 1),
            "production_batch": f"BATCH_{t.strftime('%Y%m%d')}_{rng.randint(1, 5):02d}",
            "mes_reason_code": cause if auto_coded else GENERIC_MES_CODE, "period": period,
            "verified_root_cause": cause, "corrective_action": act["text"],
        })
    df = pd.DataFrame(rows)
    if inject_flaws and len(df) > 120:  # raw-data flaws for the cleaning pipeline / edge-case tests
        df.loc[12, "machine_state"] = "UNKNOWN_ERR_STATE"
        df.loc[45, "stoppage_duration_seconds"] = -15.0
        df.loc[78, "stoppage_duration_seconds"] = 1.0
        df.loc[100, "event_id"] = df.loc[99, "event_id"]
    if save:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Generated {len(df)} records -> {output_path}")
    return df


if __name__ == "__main__":
    generate_synthetic_dataset()
