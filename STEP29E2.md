# Step 29E.2 — Real session state fault regression tests

Adds `backend/tests/test_motion_fault_real_session_states.py` (4 tests). No production code changes.

Tests exercise the actual `AutoSessionService`, `CalibrationSessionService`, and `RollerHomingService` fault handlers with mocked dependencies, no hardware commands.

- AUTO: fault latch, stop running/paused state, invalidate position, reject restart and coordinated recovery while prepared session remains.
- CALIBRATION: discard session, saved flag, auto mode; reject restart and access until recovery.
- HOME: invalidate Point0, mark fault, keep ownership, avoid extra STOP; test both active and completed HOME.

These tests do **not** prove the full runtime-to-session integration, physical stop, timing, or safety certification.

## Apply

```bash
unzip -o ~/Downloads/washing-machine-step29e2-real-session-tests.zip -d .
docker compose exec backend python -m pytest -q tests/test_motion_fault_real_session_states.py
docker compose exec backend python -m pytest -q
```

Expected total: 815 (811 prior + 4 new).

## Commit

```bash
git add backend/tests/test_motion_fault_real_session_states.py STEP29E2.md
git commit -m "Test AUTO calibration and HOME fault state transitions"
git push origin main
```
