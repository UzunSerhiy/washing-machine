# Step 29D — REAL motion preflight fault latch

Before this change, a failed `require_motion_fault_free` inside `Machine._execute_motion` blocked that individual RUN but did not latch the failure or attempt STOP all drives.

Now an existing latch is rejected immediately. A fresh preflight failure (E15, invalid/unavailable telemetry) enters the same fail-closed handler as a command dispatch failure: in-memory latch, best-effort persistent write, best-effort STOP all, original exception re-raised. This is limited to REAL (`enforce_motion_preflight=True`). No RESET or automatic RUN is sent. Physical stop is not inferred from STOP commands.

Tests: `tests/test_motion_preflight_failure_latch.py` (8 tests). Full suite should be run in Docker; local collection is blocked by missing `asyncpg`.

Install from project root: `unzip -o washing-machine-step29d-preflight-latch.zip -d .`

Run: `docker compose exec backend python -m pytest -q tests/test_motion_preflight_failure_latch.py` then `docker compose exec backend python -m pytest -q`.

Caution: the software latch and monitoring are not safety-rated and do not replace wired emergency stop. Do not test real motion based on this patch alone.
