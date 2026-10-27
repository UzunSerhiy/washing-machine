# STEP31E — AUTO / CALIBRATION frontend diagnostics

Adds the existing readiness and motion-fault polling to AUTO and CALIBRATION.
Commands capable of initiating motion are disabled on stale, missing, faulted or unready diagnostics.
Stop / pause actions remain available (backend remains authoritative).

Install from repository root: `unzip -o washing-machine-step31e-auto-calibration-diagnostics.zip -d .`
Verify: `cd frontend && npm run lint && npm run build`.
Do not test motor motion on real hardware.
