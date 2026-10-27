# Step 31Ж — unified frontend diagnostic freshness

All MANUAL/AUTO/CALIBRATION pages now use one `useMotionUiDiagnostics()` hook. UI start commands are disabled when diagnostic responses are pending, fetching, errored, older than 3 seconds, not ready, or motion fault is latched. STOP paths remain unchanged.

## Checks (no physical motion)
1. `cd frontend && npm run lint && npm run build`.
2. With backend restart latch, verify all three pages show the latch reason and motion buttons disabled.
3. In browser developer tools, block the `/api/machine/readiness` and `/api/machine/motion-fault` requests; confirm all pages show missing/stale diagnostic warning and motion buttons disabled.
4. Restore requests: if backend latch remains, all pages must still block motion.
5. Check STOP controls remain available when their existing mode/session conditions permit.

These are UI checks, not proof of motor safety. Do not clear E15 or start motors to test.
