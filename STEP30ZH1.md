# Step 30Ж.1 — serialize MANUAL dispatch and mode changes

A per-operation-service `RLock` now serializes MANUAL motion commands, speed changes, stage navigation and mode transitions. Mode transitions hold the lock through `stop_all()` and the state update, so an already admitted MANUAL RUN cannot dispatch after the mode-switch STOP. This is an application-level concurrency guard, not a hardware safety interlock. It does not serialize AUTO/CALIBRATION/HOME against mode changes, which require separate audit and tests.

Run `docker compose exec backend python -m pytest -q tests/services/machine/test_step30zh_mode_serialization.py` then full pytest. Do not operate real drives for this test. Do not commit until full suite passes.
