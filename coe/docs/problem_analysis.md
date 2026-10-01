# Problem Analysis

**Plant:** assembly cells where operators and collaborative robots (cobots) share a workspace (10 stations, 3 shifts).

**Problem:** Micro-stoppages (seconds to a few minutes) are logged by the MES as downtime under a generic code
(`UNCLASSIFIED_MICROSTOP`). Only stops the controller can name by itself (safety stop, tool change) get a cause. In the synthetic
plant, ~88% of all stoppage time is hidden this way. Each stop is too small to investigate, but together they dominate lost time, and
the *recurring causes* (a worn fixture pin on Product A in Shift 2, a dusty photo-eye on stations 1-5, material arriving late on nights)
are invisible because nobody sums them by cause, context and shift.

**Why existing tools fail**
* MES reports total downtime, not why. Pareto by `machine_state` is misleading: the same state (WAITING_FOR_OPERATOR) hides several causes.
* Operator notes hold the cause but are free text in English, Tamil and Tanglish ("sensor block aachu"), often missing.
* Nobody closes the loop: after a fix, was the stoppage rate actually reduced?

**Solution:** a micro-stoppage pattern miner that (1) attributes each stop to a probable root cause from machine states, operator notes,
product, shift, station and duration, (2) mines recurring patterns with context, (3) quantifies hidden downtime, (4) proposes a
corrective action, and (5) statistically verifies the action using pre/post stoppage rates, with a human sign-off.

**Success definition** (fixed before experiments, see `src/utils/config.py::TARGETS`): macro-F1 >= 0.80 and >= +0.10 over the baseline;
>= 80% of hidden-downtime seconds attributed correctly; top-cause downtime error <= 10%; >= 75% of effective actions verified and
the ineffective one rejected; robustness drop <= 0.15 under failure states; unseen causes not confidently mislabelled.

**Scope limits:** synthetic data; not a real-time safety system (never touches robot control); not for individual performance monitoring.
