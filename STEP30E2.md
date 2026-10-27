# Шаг 30Е.2 — AUTO session generation

- AUTO prepare captures a generation before asynchronous database reads and validates it before publication.
- AUTO start, tick and resume validate the captured session generation.
- WindingController forwards the session generation into Machine.start_roller_forward, where the validation and RUN dispatch occur under the Machine lock.
- AUTO stop clears its generation.
- Legacy direct WindingController usage remains supported without a session token.

## Important
This is a code patch for AUTO only. HOME and CALIBRATION are not covered.
Run the full pytest suite in Docker before committing. Do not test on live rotating hardware.
