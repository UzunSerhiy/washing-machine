# Step 29ZH — HTTP recovery tests

Adds ASGI-level tests for `POST /api/machine/motion-fault/acknowledge` with mocked GAIN telemetry. No actual drives are connected, and FastAPI lifespan is not started.

Covers operator confirmation, E15, RS-485 timeout, non-STOP, nonzero frequency, prepared AUTO, cleanup failure, successful acknowledgement, and repeated acknowledgement.

The tests do not establish physical stopping, E-STOP integrity, or durable startup behavior; those require separate verification. No production code changes.

Run:

```bash
docker compose exec backend python -m pytest -q tests/test_motion_fault_http_recovery.py
docker compose exec backend python -m pytest -q
```
