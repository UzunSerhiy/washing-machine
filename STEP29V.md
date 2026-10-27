# Step 29V — RUN/monitor concurrency regression tests

The current `Machine._roller_lock` already serializes `poll_motion_faults()` with
`start_brush()`, `start_roller_forward()` and `start_roller_reverse()`.
The new tests document this property and verify a fault observed by the monitor
blocks a subsequently queued RUN.

No production code changed. Tests use mocks and do not communicate with drives.

## Apply

    unzip -o washing-machine-step29v-run-monitor-tests.zip -d .
    docker compose exec backend python -m pytest -q tests/test_motion_fault_run_races.py
    docker compose exec backend python -m pytest -q

## Limitations

The lock does not give the monitor preemption or priority over an already running
motion operation. It cannot make fault-check and RUN atomic with respect to a
physical E15 appearing on the drive. A wired E-STOP is essential. Direct driver
calls outside Machine are not protected by this Machine lock. This is not a
safety-rated interlock.
