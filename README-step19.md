# Step 19 — HOME timing diagnostics

This patch only adds monotonic timing measurements to RollerHomingService.get_status()['timing']. It does not enable REAL homing, change movement frequency, change stop logic, or send additional commands.

Events: pulse_detected_at (when the service tick observes the sensor pulse), stop_requested_at, stop_command_returned_at, stop_confirmed_at (after three consecutive stop observations). Times are monotonic process-local seconds; durations are milliseconds. These are **software observation timings**, not hardware timestamps or measurements of physical shaft deceleration.

Install from repository root:

    unzip -o ~/Downloads/washing-machine-step19-home-timing.zip -d .
    docker compose exec backend python -m pytest -q

If tests pass:

    git add backend/app/services/machine/roller_homing_service.py backend/tests/test_homing_timing_diagnostics.py
    git commit -m "feat: record HOME stop timing diagnostics"
    git push origin main

To see diagnostics when the existing HOME service reports them, inspect GET /api/machine/home; the API may expose only selected status fields. No new HTTP endpoint is added in this patch.

Local check: 9 focused tests passed. Full local test suite could not be collected because pymodbus is missing outside Docker.
