# Step 32В — recovery responsiveness

- Recovery telemetry no longer holds machine roller RLock during serial reads.
- Logs sample/drive/register name, and failing read.
- Acknowledge HTTP wait is bounded to 15 seconds (504); background verification is NOT cancelled on timeout, and the polling exclusion is retained until completion. Do not retry while it is running.
- Does not bypass STOP/fault checks or issue VFD RUN/RESET commands.

Install from project root: `unzip -o ~/Downloads/washing-machine-step32v-recovery-fix.zip -d .` then `docker compose up -d --build backend`.

IMPORTANT: On HTTP 504 the request may finish later and acknowledge the software latch if all checks succeed. Before applying, ensure physical E-STOP prevents any movement and do not use this patch as a safety-rated control. Inspect logs and verify machine state after timeout.
