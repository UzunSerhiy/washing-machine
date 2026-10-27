# Step 29E — fault propagation regression tests

Four hardware-free tests cover dispatch failure, persistent machine latch, asynchronous notification on the next monitor poll, isolation of a failing session callback, and absence of automatic RUN.

**Important limitation:** the tests use mock session handlers; they do not prove that the real AUTO, CALIBRATION and HOME state machines always reach safe states. A callback that fails after partially mutating a real session is not automatically retried by `MotionFaultRuntime`. This remains a follow-up audit item.

Run:

```bash
docker compose exec backend python -m pytest -q tests/test_motion_fault_session_propagation.py
docker compose exec backend python -m pytest -q
```

No physical motor movement is authorized by this patch.
