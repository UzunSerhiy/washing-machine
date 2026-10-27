import test from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import { QueryClient } from '@tanstack/react-query';
import { evaluateMotionUiDiagnostics } from '../lib/motion-ui-diagnostics.mjs';

// In-memory HTTP adapter. No network, RS485, ESP32 or motor commands.
const HEALTHY = {
  readiness: { ready: true, reasons: [], diagnostic_only: true },
  fault: { latched: false, reason: null, diagnostic_only: true },
};
const KEYS = { readiness: ['machine', 'readiness'], fault: ['machine', 'motion-fault'] };
function rig() {
  const responses = structuredClone(HEALTHY);
  const failures = new Set();
  const requests = [];
  const client = axios.create({ adapter: async (config) => {
    requests.push({ method: config.method, url: config.url });
    assert.equal(config.method, 'get', 'Only diagnostic GET requests are permitted');
    const kind = config.url === '/api/machine/readiness' ? 'readiness'
      : config.url === '/api/machine/motion-fault' ? 'fault' : null;
    assert.ok(kind, `Unexpected endpoint: ${config.url}`);
    if (failures.has(kind)) throw new axios.AxiosError('Mock connection lost', 'ECONNABORTED', config);
    return { data: structuredClone(responses[kind]), status: 200, statusText: 'OK', headers: {}, config };
  }});
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  async function fetch(kind) {
    return cache.fetchQuery({ queryKey: KEYS[kind], staleTime: 0,
      queryFn: async () => (await client.get(`/api/machine/${kind === 'fault' ? 'motion-fault' : 'readiness'}`)).data });
  }
  async function refresh() { await Promise.allSettled([fetch('readiness'), fetch('fault')]); }
  function snapshot(kind) {
    const state = cache.getQueryState(KEYS[kind]);
    return {
      isPending: !state || state.status === 'pending',
      isError: state?.status === 'error',
      isFetching: cache.isFetching({ queryKey: KEYS[kind], exact: true }) > 0,
      dataUpdatedAt: state?.dataUpdatedAt ?? 0,
      data: state?.data,
    };
  }
  function evaluate(now = Date.now()) {
    return evaluateMotionUiDiagnostics(now, snapshot('readiness'), snapshot('fault'));
  }
  return { responses, failures, requests, cache, fetch, refresh, snapshot, evaluate };
}

test('initial state fails closed until both HTTP diagnostics arrive', async () => {
  const r = rig();
  assert.equal(r.evaluate().allowed, false);
  await r.fetch('readiness');
  assert.equal(r.evaluate().allowed, false);
  await r.fetch('fault');
  assert.equal(r.evaluate().allowed, true);
  assert.deepEqual(r.requests.map(x => x.url), ['/api/machine/readiness', '/api/machine/motion-fault']);
});

test('E15 latched by HTTP response blocks despite ready=true', async () => {
  const r = rig();
  r.responses.fault = { latched: true, reason: 'E15', diagnostic_only: true };
  await r.refresh();
  assert.equal(r.evaluate().allowed, false);
  assert.match(r.evaluate().reason, /E15/);
});

test('connection failure blocks even with previously cached healthy response', async () => {
  const r = rig();
  await r.refresh();
  assert.equal(r.evaluate().allowed, true);
  r.failures.add('fault');
  await r.refresh();
  assert.equal(r.snapshot('fault').isError, true);
  assert.equal(r.evaluate().allowed, false);
});

test('stale successful HTTP responses are rejected without a refetch', async () => {
  const r = rig();
  await r.refresh();
  const newest = Math.max(r.snapshot('readiness').dataUpdatedAt, r.snapshot('fault').dataUpdatedAt);
  assert.equal(r.evaluate(newest + 3000).allowed, false);
});

test('reconnection does not remove server-latched fault; only new unlatched response does', async () => {
  const r = rig();
  r.responses.fault = { latched: true, reason: 'operator acknowledgement required', diagnostic_only: true };
  await r.refresh();
  r.failures.add('readiness');
  await r.refresh();
  assert.equal(r.evaluate().allowed, false);
  r.failures.delete('readiness');
  await r.refresh();
  assert.equal(r.evaluate().allowed, false);
  assert.match(r.evaluate().reason, /operator acknowledgement/);
  // Simulated backend state change only; this test does NOT send an acknowledgement.
  r.responses.fault = { latched: false, reason: null, diagnostic_only: true };
  await r.refresh();
  assert.equal(r.evaluate().allowed, true);
  assert.ok(r.requests.every(x => x.method === 'get'));
});
