import test from "node:test";
import assert from "node:assert/strict";
import { evaluateMotionUiDiagnostics as evaluate } from "../lib/motion-ui-diagnostics.mjs";

const NOW = 10_000;
function snapshots() {
  return {
    readiness: { isPending: false, isError: false, isFetching: false, dataUpdatedAt: NOW - 100, data: { ready: true, reasons: [], diagnostic_only: true } },
    fault: { isPending: false, isError: false, isFetching: false, dataUpdatedAt: NOW - 100, data: { latched: false, reason: null, diagnostic_only: true } },
  };
}

test("fresh healthy snapshots allow UI controls (not physical authorization)", () => {
  const { readiness, fault } = snapshots();
  assert.equal(evaluate(NOW, readiness, fault).allowed, true);
});

test("latched fault blocks controls even when readiness says ready", () => {
  const { readiness, fault } = snapshots();
  fault.data = { latched: true, reason: "E15", diagnostic_only: true };
  const result = evaluate(NOW, readiness, fault);
  assert.equal(result.allowed, false);
  assert.match(result.reason, /E15/);
});

test("API error, pending or in-flight request blocks controls", () => {
  for (const key of ["isError", "isPending", "isFetching"]) {
    for (const source of ["readiness", "fault"]) {
      const pair = snapshots();
      pair[source][key] = true;
      assert.equal(evaluate(NOW, pair.readiness, pair.fault).allowed, false, `${source}.${key}`);
    }
  }
});

test("stale, missing and future timestamps block controls", () => {
  for (const timestamp of [0, NOW - 3000, NOW + 1]) {
    for (const source of ["readiness", "fault"]) {
      const pair = snapshots();
      pair[source].dataUpdatedAt = timestamp;
      assert.equal(evaluate(NOW, pair.readiness, pair.fault).allowed, false, `${source} timestamp ${timestamp}`);
    }
  }
  const pair = snapshots();
  assert.equal(evaluate(0, pair.readiness, pair.fault).allowed, false);
});

test("reconnection cannot clear a latched fault", () => {
  const pair = snapshots();
  pair.fault.data = { latched: true, reason: "operator acknowledgement required", diagnostic_only: true };
  assert.equal(evaluate(NOW, pair.readiness, pair.fault).allowed, false);
  assert.match(evaluate(NOW, pair.readiness, pair.fault).reason, /operator acknowledgement/);
});

test("not-ready or non-diagnostic responses block controls", () => {
  const pair = snapshots();
  pair.readiness.data = { ready: false, reasons: ["RS485 unavailable"], diagnostic_only: true };
  assert.equal(evaluate(NOW, pair.readiness, pair.fault).allowed, false);
  assert.match(evaluate(NOW, pair.readiness, pair.fault).reason, /RS485 unavailable/);
  pair.readiness.data = { ready: true, reasons: [], diagnostic_only: false };
  assert.equal(evaluate(NOW, pair.readiness, pair.fault).allowed, false);
  pair.readiness.data.diagnostic_only = true;
  pair.fault.data.diagnostic_only = false;
  assert.equal(evaluate(NOW, pair.readiness, pair.fault).allowed, false);
});
