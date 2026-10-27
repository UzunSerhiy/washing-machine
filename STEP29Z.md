# Step 29Z — persistent motion interlock restart regression tests

Only tests and documentation; no production code changes. Tests use temporary JSON state and mock GAIN drives; no Docker restart or physical movement.

Scenarios: E15 latch across restart; acknowledged state re-latched at REAL startup; missing/malformed state (4 cases); startup persistence failure; stale acknowledged disk state after a failed fault write.

Run:

```bash
docker compose exec backend python -m pytest -q tests/test_motion_fault_restart_cycle_step29z.py
docker compose exec backend python -m pytest -q
```

A successful test run is not proof of physical standstill or a safety-rated interlock. Physical RESET and independent wired E-STOP remain necessary. No automatic RUN is performed.
