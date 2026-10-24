# Calibration motion v2 (patch over project root)

Contains full replacement files. Do NOT overlay on an older source tree without comparing changes.

- Manual Water Start: first Reverse starts brushes, Pause stops both, subsequent jog moves roller only.
- Water Start mark starts automatic reverse at 10 Hz with brushes until Material Start.
- Washing Stop manual reverse and forward bounded by 0 and Material Start.
- After PostgreSQL commit session remains active with saved=true; separate Auto Wind at 10 Hz to Material End.
- Pause/resume automatic motion; Stop cancels it.
- Coordinates are estimated from frequency/time, not encoder; STOP can overshoot in real hardware.
- Test in fake mode first.
- Existing migration a83f1b09d627 included: run alembic upgrade head once.

**Warning:** 10 Hz is the current UI maximum, not necessarily the hardware maximum. Confirm limits and stopping behavior before live use.
