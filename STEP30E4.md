# Step 30E.4 — CALIBRATION motion generation

- Capture a motion epoch after shared HOME verification, before constructing the calibration session.
- Retain it in the session service and player.
- Validate the epoch on every `get_current()` and `tick()` before updating position.
- Forward `session_generation` to `Machine.start_brush`, `Machine.start_roller_forward`, and `Machine.start_roller_reverse`. The real Machine verifies the epoch under the motion dispatch lock.
- Discard the token on cancel, finish and external motion fault.
- Existing standalone `CalibrationPlayer` tests remain compatible: without a session token, calls retain their original signature; the production service always assigns one.
- New tests verify stale JOG, brush, direct player dispatch, tick, and fault recovery.

## Install

From repository root:

```bash
unzip -o ~/Downloads/washing-machine-step30e4-calibration-generation.zip -d .
docker compose exec backend python -m pytest -q tests/services/machine/calibration/
docker compose exec backend python -m pytest -q
```

Do not commit until the full Docker suite passes. No real drive RUN or software E15 reset is part of this patch.
