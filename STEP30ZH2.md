# Step 30Ж.2 — AUTO/mode serialization

- Serialize AUTO start/tick/pause/resume/stop with MachineOperationService._mode_lock.
- Increment mode revision on every mode transition.
- During async AUTO prepare, validate captured mode revision under mode lock before publishing session.
- Reject a prepared AUTO session after switching modes away and back.
- No physical VFD operations in tests.

## Verify

```bash
docker compose exec backend python -m pytest -q tests/services/machine/auto/ tests/services/machine/test_step30zh_mode_serialization.py
docker compose exec backend python -m pytest -q
```

Do not commit until full suite passes. This patch does not yet cover CALIBRATION/HOME cross-mode interleavings.
