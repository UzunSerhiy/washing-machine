# STEP31D — frontend diagnostics (manual)

The manual screen now polls `/api/machine/readiness` and `/api/machine/motion-fault` every second.
It does not enable START, FORWARD, REVERSE, or speed changes unless both diagnostics are
fresh, successful, and report ready/no latched fault. Pending or failed refreshes fail closed.
STOP remains available in manual mode even when diagnostics fail.

**Limitations:** This is UI gating only, not an interlock or safety-rated E-STOP.
The backend must independently validate each motion command. A browser disconnect cannot
stop a running motor. Readiness is a read-only diagnostic and is not motion authorization.

Verification: `cd frontend && npm ci && npm run lint && npm run build`.
Check manually with mock backend: normal readiness, latched E15, HTTP 503, and disconnected backend.
No real motor RUN or E15 reset is required.
