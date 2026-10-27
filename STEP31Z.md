# №31З — UI diagnostic regression tests

Extracted the existing pure decision logic from `useMotionUiDiagnostics` without changing its conditions. Tests use Node built-in `node:test`, without new npm dependencies.

Run from `frontend/`: `npm run test:safety`, `npm run lint`, `npm run build`.

These are unit tests of UI diagnostic decisions, not React rendering, HTTP transport, backend interlocks or physical E-STOP. Do not run motors for these tests.
