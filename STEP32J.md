# Step 32J — REAL HOME button in MANUAL

Based on v63. Existing HOME algorithm, limits, stop confirmation, fault latch and mode/ownership checks remain unchanged. The API no longer rejects REAL solely due to DRIVE_MODE; it still calls operation.start_home() and RollerHomingService.start().

This patch adds a MANUAL HOME control with operator confirmation, 1–10 Hz selection, sensor and HOME state polling, and software cancel. This is *not* the two-second fine-positioning algorithm: that algorithm is not implemented by this patch. HOME requires verified external stop/fault controls; a software stop is not a safety-rated E-STOP.

Install from repository root:
  unzip -o ~/Downloads/washing-machine-step32j-real-home-manual.zip -d .
  cd frontend && npm run lint && npm run build
  cd .. && docker compose up -d --build backend

Do not issue a motion command merely to test the UI; first inspect the configuration and stop chain.
