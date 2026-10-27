# Шаг 30Е.3 — HOME session generation

HOME captures the motion generation before waiting on its state lock. The generation is checked before state transition and passed to `Machine.start_roller_reverse`, where the epoch is checked atomically with the RUN dispatch. HOME tick, completion and stop confirmation validate the original generation. A stale HOME tick invalidates Point 0 without issuing a new RUN or a STOP that might interfere with a newer roller owner.

Legacy mock-only HOME callers retain the existing interface. Tests use mocked drives and sensor.

Run:

```bash
docker compose exec backend python -m pytest -q tests/test_step30e3_home_generation.py
docker compose exec backend python -m pytest -q
```

Do not test on rotating hardware. No software action resets E15 or substitutes for physical E-STOP/RESET.
