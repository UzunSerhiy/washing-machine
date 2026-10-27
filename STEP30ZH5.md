# №30Ж.5 — Regression tests for stale motion sessions after E15

Tests use `Machine` and `MotionFaultRecoveryService` with mocked drives and services. No real hardware, RUN, STOP or RESET is performed.

Scenarios: (1) old AUTO/HOME/CALIBRATION generation tokens cannot dispatch brush/roller RUN after successful recovery; (2) physical RESET telemetry alone does not clear software latch; (3) unsuccessful STOP verification retains latch; (4) session cleanup failure retains latch. This verifies the machine-level epoch boundary, not complete end-to-end session concurrency or physical E-STOP performance.

Run: `docker compose exec backend python -m pytest -q tests/test_step30zh5_stale_sessions.py` and full suite. Expected: 901 tests (897 + 4). Do not commit before Docker full suite passes.
