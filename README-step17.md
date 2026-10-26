# Step 17 — REAL roller VFD stop telemetry wiring

Connects the existing read-only stop observer to RollerHomingService during app startup when DRIVE_MODE=real. Uses the same roller drive instance as the Machine. No motion commands or REAL homing endpoint changes. FAKE behavior is unchanged.

Install from project root:

    unzip -o ~/Downloads/washing-machine-step17-real-stop-wiring.zip -d .
    docker compose exec backend python -m pytest -q

Restart backend after tests, once ready to deploy:

    docker compose up -d --build backend

NOTE: This is NOT a REAL HOME unlock. Physical homing still requires an independent emergency stop and verified mechanical stopping behavior. VFD telemetry alone does not prove shaft is stationary.
