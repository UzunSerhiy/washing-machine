# Step 16 — HOME stop confirmation integration

Changes: `RollerHomingService` optionally accepts `stop_observer` (a zero-argument callable returning `StopObservation`). After the HOME sensor event and STOP command, it waits for three consecutive confirmed telemetry samples, with a five-second timeout. An error latches a fault and retains roller ownership. `awaiting_stop_confirmation` is exposed in status. A second HOME cannot start while confirmation is pending.

**Important:** The existing `main.py` is not changed; REAL homing remains blocked by its existing route guard. This patch does not activate physical motion. The callback is not yet wired into the application startup. The legacy behavior remains for callers without a callback. VFD telemetry alone does not verify mechanical shaft standstill or exact angular Point0.

Installation from project root:

```bash
unzip -o ~/Downloads/washing-machine-step16-homing-stop-integration.zip -d .
docker compose exec backend python -m pytest -q
```

If successful:

```bash
git add backend/app/services/machine/roller_homing_service.py backend/tests/test_homing_stop_integration.py
git commit -m "feat: integrate stop confirmation into homing lifecycle"
git push origin main
```

Local run: 23 focused tests passed. Full suite unavailable in local container due to missing `pymodbus`; run in your backend Docker container.
