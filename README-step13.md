# Step 13 — Shared Point0 dialog (read-only)

Adds the same Point0 / HOME entry point to MANUAL, AUTO and CALIBRATION.
The dialog polls the existing `/api/machine/home` and roller-reference sensor endpoints.

**This patch deliberately does not send motion commands.** Forward/Reverse/Stop and auto-seek are disabled until backend hold-to-run watchdog, machine state gating, and stop/fault behavior are implemented and tested. Existing REAL homing restrictions remain unchanged.

Install from project root:

```sh
unzip -o ~/Downloads/washing-machine-step13-point0-ui.zip -d .
docker compose exec backend python -m pytest -q
docker compose up -d --build frontend
```

Check `git diff` before committing.
