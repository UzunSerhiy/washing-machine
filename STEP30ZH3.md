# Step 30Ж.3 — HOME / CALIBRATION mode serialization

- HOME checks MANUAL and starts under the shared operation mode lock.
- CALIBRATION start switches mode and creates session atomically at API level.
- CALIBRATION session actions/tick use the shared mode lock; stale sessions reject a changed mode revision.
- Physical E-STOP and RESET behavior is unchanged. Tests use fake hardware only.

Run: `docker compose exec backend python -m pytest -q`.
