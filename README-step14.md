# Step 14 — REAL Point0 diagnostics (no motion)

Apply on top of step 13. This patch corrects the shared HOME endpoint and frontend status type and exposes the actual shared HOME status, sensor pulses and fault state in the Point0 dialog.

No motor commands are enabled. Backend is unchanged. REAL HOME remains blocked until verified independent emergency stop and feedback-based stopped confirmation are implemented.

Install: unzip -o ~/Downloads/washing-machine-step14-real-point0-diagnostics.zip -d .
