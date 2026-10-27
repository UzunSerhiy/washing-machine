# Step 30ZH.6 — session lifecycle after fault recovery

Test-only patch based on v51 / commit 090d64a.

Three regression tests exercise the **real** AUTO, CALIBRATION and HOME service fault/recovery methods, a mocked Machine and mocked VFD telemetry. They check:

1. External E15 notification clears session activity, invalidates HOME and AUTO position, coordinated acknowledgement clears the software latch, and a pre-fault generation cannot send RUN.
2. An AUTO state unexpectedly still marked running blocks acknowledgement and retains the latch.
3. An active CALIBRATION session blocks acknowledgement and retains the latch.

These tests do not assert physical E-STOP or RESET behaviour. No physical drives are used, and no production code is changed.

Run:

```bash
docker compose exec backend python -m pytest -q tests/test_step30zh6_service_lifecycle.py
docker compose exec backend python -m pytest -q
```

Expected full suite: 904 tests (901 + 3). Do not commit before Docker results.
