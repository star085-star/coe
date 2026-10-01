# Error Analysis (auto-generated)

## Where the prototype is wrong
Top confusions (held-out events): | True | Predicted | Count |
|---|---|---|
| OPERATOR_LOADING_DELAY | MATERIAL_MISALIGNMENT | 35 |
| OPERATOR_LOADING_DELAY | QUALITY_INSPECTION_DELAY | 28 |
| OPERATOR_LOADING_DELAY | TOOL_CHANGE | 22 |
| MATERIAL_MISALIGNMENT | OPERATOR_LOADING_DELAY | 21 |
| OPERATOR_LOADING_DELAY | ROBOT_RECOVERY | 18 |
| OPERATOR_LOADING_DELAY | MATERIAL_SHORTAGE | 17 |

The confused pairs share the WAITING / IDLE / BLOCKED family of machine states and similar "waiting" wording in notes, i.e. exactly the causes a human also finds hard to separate from the log alone.

## Language of the operator note
| Note language | Events | Accuracy |
|---|---|---|
| en | 4464 | 0.943 |
| none | 733 | 0.835 |
| ta | 982 | 0.967 |
| tanglish | 1170 | 0.953 |

Notes in Tamil script and Tanglish are not penalised (character n-grams + concept lexicon), but this is on synthetic phrases written for the generator; real free text will be harder. Events with **no note** are the weakest group.

## Misleading machine state
Accuracy when the logged state is the typical one for that cause: 0.962; when the state is misleading: **0.905** (baseline: 0.138).
This is the core reason the baseline fails: it trusts machine_state alone.

## Confidence is informative
Mean confidence when correct 0.965 vs when wrong 0.702 -> low-confidence events can be queued for human review.

## Highest-confidence mistakes (with the features that drove the prediction)
* `EVT_003994` true **SAFETY_ZONE_INTERRUPTION**, predicted **MATERIAL_MISALIGNMENT** (conf 1.0); state=INSPECTION_HOLD; note="reset done"; drivers: [('workstation_id_WS_01', 3.73), ('material_status_MISALIGNED', 2.5), ('product_Product_A', 2.061), ('robot_mode_COLLABORATIVE', 1.85), ('next_machine_state_RECOVERY', 1.363)]
* `EVT_006864` true **OPERATOR_LOADING_DELAY**, predicted **QUALITY_INSPECTION_DELAY** (conf 1.0); state=TOOL_CHANGE; note="checking dimension variance"; drivers: [('product_Product_D', 3.114), ('robot_mode_COLLABORATIVE', 1.407), ('quality_status_MARGINAL', 1.164), ('material_status_PRESENT', 0.956), ('ct_quality', 0.783)]
* `EVT_010095` true **ROBOT_RECOVERY**, predicted **TOOL_CHANGE** (conf 0.999); state=TOOL_CHANGE; note="robot stop aachu reset panninom"; drivers: [('machine_state_TOOL_CHANGE', 4.347), ('log_duration', 1.925), ('safety_zone_status_MUTED', 1.547), ('product_Product_A', 0.758), ('next_machine_state_RUNNING', 0.685)]
* `EVT_001942` true **TOOL_CHANGE**, predicted **MATERIAL_MISALIGNMENT** (conf 0.999); state=IDLE; note="material alignment issue on fixture"; drivers: [('workstation_id_WS_01', 3.73), ('material_status_MISALIGNED', 2.5), ('product_Product_A', 2.061), ('sensor_status_OK', 0.608), ('ct_align', 0.442)]
* `EVT_006848` true **OPERATOR_LOADING_DELAY**, predicted **MATERIAL_SHORTAGE** (conf 0.999); state=IDLE; note=""; drivers: [('machine_state_IDLE', 2.974), ('robot_mode_AUTOMATIC', 2.4), ('material_status_EMPTY', 2.138), ('shift_Shift_1', 1.047), ('safety_zone_status_CLEAR', 1.04)]

## Estimator error in action verification
| Cause | Assumed true effect % | Measured % (deployed labels) | Measured % (perfect labels) | Error pp |
|---|---|---|---|---|
| MATERIAL_MISALIGNMENT | 65.0 | 67.8 | 68.4 | 2.8 |
| SENSOR_INTERRUPTION | 70.0 | 68.0 | 68.9 | -2.0 |
| OPERATOR_LOADING_DELAY | 45.0 | 42.8 | 43.2 | -2.2 |
| SAFETY_ZONE_INTERRUPTION | 35.0 | 39.6 | 39.6 | 4.6 |
| ROBOT_RECOVERY | 3.0 | 6.6 | 2.7 | 3.6 |

Errors come from (a) sampling noise in counts, (b) label noise that dilutes or shifts events between causes. The intervals are exact binomial; they cover the assumed effect in most rows but are not guaranteed to for the effect of an action on a mislabelled neighbour cause.

## Unseen cause and unknown clusters
Unseen-cause abstention was 0.0181 (target 0.5): failed. Clusters formed from abstained events (for human review): [{"cluster": 1, "events": 49, "downtime_hours": 0.28, "top_state": "BLOCKED", "top_workstation": "WS_09", "example_notes": ["seri aayiduchu", "minor pause", "reset done"]}, {"cluster": 2, "events": 49, "downtime_hours": 0.31, "top_state": "WAITING_FOR_OPERATOR", "top_workstation": "WS_02", "example_notes": ["test run", "test run", "restarted"]}]
