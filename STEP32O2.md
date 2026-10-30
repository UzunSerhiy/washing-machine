# STEP 32O.2 — Point0 jog

From v65 + step32O stage1. Adds shared Point0 positioning pulses on MANUAL/AUTO/CALIBRATION without changing selected mode. Each press sends a bounded 2-second jog at 1–10 Hz, followed by STOP and three consecutive stopped-VFD observations. The existing HOME zero is invalidated when positioning starts. While Point0 owns the roller, new motion and mode changes are blocked. Backend+frontend rebuild required.

CAUTION: Software timers and VFD telemetry are not safety-rated, and a backend/host failure can interrupt the timer. Keep physical E-STOP accessible and verify VFD communication-loss behavior. STOP confirmation is VFD telemetry, not proof of a stationary shaft. Do not treat this as safety certification.
