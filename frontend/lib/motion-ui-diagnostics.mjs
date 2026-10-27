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
export function evaluateMotionUiDiagnostics(now, readiness, fault) {
  const current = now > 0 &&
    !readiness.isPending && !readiness.isError && !readiness.isFetching &&
    !fault.isPending && !fault.isError && !fault.isFetching &&
    readiness.dataUpdatedAt > 0 && fault.dataUpdatedAt > 0 &&
    now >= readiness.dataUpdatedAt && now >= fault.dataUpdatedAt &&
    now - readiness.dataUpdatedAt < 3000 && now - fault.dataUpdatedAt < 3000;

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
