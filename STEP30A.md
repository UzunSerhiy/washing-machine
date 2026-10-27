# Step 30A: read-only diagnostic consistency

- `/api/machine/readiness` now reports `MOTION_FAULT_LATCHED` even when all drives report STOP and 0 Hz.
- `/api/machine/motion-fault` no longer hardcodes `recovery_available: false`; it indicates whether the software acknowledgement endpoint is configured, **not** whether physical RESET happened or recovery will succeed.
- `recovery_note` clarifies physical RESET, operator confirmation and telemetry verification.
- No RUN, STOP, RESET, HOME or fault-clear logic changed.
- Do not use readiness or recovery_available as authorization to move.

Run:

```sh
docker compose exec backend python -m pytest -q tests/test_step30a_diagnostics.py tests/test_machine_readiness_diagnostics.py tests/test_motion_fault_diagnostics.py
docker compose exec backend python -m pytest -q
```
