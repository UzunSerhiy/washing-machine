/**
 * Pure UI-only diagnostic evaluation. Never authorizes motor movement.
 * @typedef {{ready:boolean, reasons:string[], diagnostic_only:boolean}} Readiness
 * @typedef {{latched:boolean, reason:string|null, diagnostic_only:boolean}} Fault
 * @typedef {{isPending:boolean,isError:boolean,isFetching:boolean,dataUpdatedAt:number,data?:Readiness}} ReadinessQuery
 * @typedef {{isPending:boolean,isError:boolean,isFetching:boolean,dataUpdatedAt:number,data?:Fault}} FaultQuery
 * @param {number} now
 * @param {ReadinessQuery} readiness
 * @param {FaultQuery} fault
 * @returns {{allowed:boolean, reason:string}}
 */
// Allow for delayed polling responses without treating a normal refetch as lost data.
// This is UI indication only; backend checks every movement command.
const MAX_DIAGNOSTIC_AGE_MS = 10000;
// The query may finish between the 500 ms clock ticks.
const MAX_CLOCK_TICK_LAG_MS = 1000;

export function evaluateMotionUiDiagnostics(now, readiness, fault) {
  const current = now > 0 &&
    !readiness.isPending && !readiness.isError &&
    !fault.isPending && !fault.isError &&
    readiness.dataUpdatedAt > 0 && fault.dataUpdatedAt > 0 &&
    readiness.dataUpdatedAt - now <= MAX_CLOCK_TICK_LAG_MS &&
    fault.dataUpdatedAt - now <= MAX_CLOCK_TICK_LAG_MS &&
    now - readiness.dataUpdatedAt < MAX_DIAGNOSTIC_AGE_MS &&
    now - fault.dataUpdatedAt < MAX_DIAGNOSTIC_AGE_MS;

  const allowed = current && readiness.data?.ready === true &&
    readiness.data?.diagnostic_only === true &&
    fault.data?.latched === false && fault.data?.diagnostic_only === true;

  const reason = fault.data?.latched
    ? `Аварийная блокировка: ${fault.data.reason ?? "причина неизвестна"}`
    : !current
      ? "Нет актуальных диагностических данных от backend"
      : readiness.data?.ready === false
        ? `Машина не готова: ${readiness.data.reasons.join(", ") || "нет подтверждения"}`
        : "Нет подтверждения готовности машины";

  return { allowed, reason };
}

/**
 * Read-only command-specific UI diagnostics. Does not grant permission to move.
 * Running drives are not a fault for speed changes or other independent drives.
 */
export function evaluateManualMotionDiagnostics(now, readiness, fault) {
  const fresh = now > 0 &&
    !readiness.isPending && !readiness.isError &&
    !fault.isPending && !fault.isError &&
    readiness.dataUpdatedAt > 0 && fault.dataUpdatedAt > 0 &&
    readiness.dataUpdatedAt - now <= MAX_CLOCK_TICK_LAG_MS &&
    fault.dataUpdatedAt - now <= MAX_CLOCK_TICK_LAG_MS &&
    now - readiness.dataUpdatedAt < MAX_DIAGNOSTIC_AGE_MS &&
    now - fault.dataUpdatedAt < MAX_DIAGNOSTIC_AGE_MS;

  const block = (reason) => ({allowed: false, reason});
  const pass = () => ({allowed: true, reason: ""});
  const denied = !fresh ? "Нет актуальных диагностических данных от backend"
    : fault.data?.latched !== false || fault.data?.diagnostic_only !== true
      ? `Аварийная блокировка: ${fault.data?.reason ?? "нет подтверждения"}`
      : readiness.data?.diagnostic_only !== true
        ? "Диагностика не подтверждена"
        : null;
  const driveList = readiness.data?.drives;
  const driveIds = [1, 2, 3];
  const drives = new Map(Array.isArray(driveList) ? driveList.map(d => [d.drive_id, d]) : []);
  const unsafe = [];
  if (denied) unsafe.push(denied);
  if (!Array.isArray(driveList) || driveIds.some(id => !drives.has(id))) unsafe.push("Нет диагностики всех трёх приводов");
  for (const id of driveIds) {
    const d = drives.get(id);
    if (!d) continue;
    const reasons = Array.isArray(d.reasons) ? d.reasons : ["INVALID_DIAGNOSTICS"];
    if (d.connected !== true || ![1,2,3].includes(d.status) ||
        !Number.isFinite(d.frequency_hz) || d.frequency_hz < 0 ||
        !Number.isInteger(d.fault) || d.fault !== 0 ||
        reasons.some(r => r !== "DRIVE_NOT_STOPPED")) {
      unsafe.push(`drive_${id}: ${reasons.join(", ") || "диагностика недостоверна"}`);
    }
  }
  if (readiness.data?.home_faulted !== false) unsafe.push("HOME_FAULT / нет данных HOME");
  if (readiness.data?.reasons?.some(r => !/^drive_[123]:DRIVE_NOT_STOPPED$/.test(r))) {
    unsafe.push(readiness.data.reasons.filter(r => !/^drive_[123]:DRIVE_NOT_STOPPED$/.test(r)).join(", "));
  }
  const shared = unsafe.length ? block(unsafe.join("; ")) : pass();
  const stopped = (ids) => {
    if (!shared.allowed) return shared;
    const running = ids.filter(id => {
      const d = drives.get(id);
      return d.status !== 3 || d.frequency_hz !== 0;
    });
    return running.length ? block(`Перед запуском остановите привод(ы): ${running.join(", ")}`) : pass();
  };
  return {
    rollerStart: stopped([3]),
    brushStart: stopped([1, 2]),
    rollerSpeed: shared,
    brushSpeed: shared,
  };
}
