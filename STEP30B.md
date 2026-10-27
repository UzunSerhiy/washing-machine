# Step 30B — E-STOP / physical RESET software contract

Adds eight **simulated** HTTP recovery checks: E15 on each of three GAIN drives,
telemetry clearing without software acknowledgement, missing operator confirmation,
RS-485 loss on each drive, successful software acknowledgement with no RUN, and a
new E15 after an earlier acknowledgement.

No production code, VFD parameters, STOP/RUN, HOME, or RESET commands are changed.

## Run

```bash
docker compose exec backend python -m pytest -q tests/test_step30b_estop_reset_contract.py
docker compose exec backend python -m pytest -q
```

Expected total: 847 tests (previous 839 + 8), if all pass.

## Important hardware safety boundary

These tests do **not** test the physical E-STOP circuit or prove safe torque removal.
Do not test E-STOP by deliberately spinning connected shafts. Have a qualified
machine electrician inspect E-STOP input wiring, input function, stop category,
restart prevention, and RESET behavior against the actual GAIN model manual.
Physical RESET must not start motion. `status=3` and `0 Hz` are VFD-reported
telemetry, not independent verification that shafts are stationary.
