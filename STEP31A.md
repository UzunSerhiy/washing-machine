# Step 31A — startup fail-closed integration regression

Test-only patch based on v52, commit `5cf56f8`. Five parametrized test cases exercise the persisted startup interlock and all three Machine motion entrypoints, malformed/missing persisted state, and invalidation of a previously captured motion generation. Mocked actuators only; no physical RUN, RESET or E-STOP. No production changes.

```bash
docker compose exec backend python -m pytest -q tests/test_step31a_startup_integration.py
docker compose exec backend python -m pytest -q
```

Expected: 5 new cases; 909 total (904 + 5). Existing unit tests already cover several individual startup behaviours; these tests consolidate the motion-admission contract at the Machine boundary. Does not verify actual process restart, frontend, ESP32, RS485 or wired safety chain.
