# Water Start + Automatic Unwinding integration

This ZIP REPLACES the earlier stage1 ZIP. Do not install both.

Includes full backend and frontend replacement files, migration a83f1b09d627.

Workflow: Material End -> Water Start (Next starts both drives, Pause stops both, Mark) -> Ready to Unwind (Next starts both, auto-stop at Material Start) -> Washing Stop (manual reverse jog, Mark) -> Complete.

CAUTION: estimated position based on frequency/time; no encoder-based closed-loop stop. Test in FAKE mode first, verify stop distance, real drives and safety interlocks before connecting equipment.

Install from repository root after backup: unzip -o /path/to/water-start-full.zip; docker compose exec -T backend alembic upgrade head; docker compose exec -T backend python -m compileall -q app; docker compose exec -T backend python -m pytest -q; cd frontend && npx tsc --noEmit

If a83f1b09d627 migration was previously installed, do not re-run older stage1 files; this ZIP includes the corrected code with the same migration revision.
