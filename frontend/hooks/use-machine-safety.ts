"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface ReadinessSnapshot {
  ready: boolean;
  reasons: string[];
  diagnostic_only: boolean;
}

export interface MotionFaultSnapshot {
  latched: boolean;
  reason: string | null;
  diagnostic_only: boolean;
}

export function useMachineReadiness() {
  return useQuery({
    queryKey: ["machine", "readiness"],
    queryFn: async () => (await api.get<ReadinessSnapshot>("/api/machine/readiness")).data,
    refetchInterval: 1000,
    staleTime: 0,
    retry: false,
  });
}

export function useMachineMotionFault() {
  return useQuery({
    queryKey: ["machine", "motion-fault"],
    queryFn: async () => (await api.get<MotionFaultSnapshot>("/api/machine/motion-fault")).data,
    refetchInterval: 1000,
    staleTime: 0,
    retry: false,
  });
}

// UI indication only. Backend interlocks and physical E-STOP remain authoritative.
// A diagnostic snapshot is not an authorization to move.
export function useMotionUiDiagnostics() {
  const readiness = useMachineReadiness();
  const fault = useMachineMotionFault();
  const [now, setNow] = useState(0);

  useEffect(() => {
    const tick = () => setNow(Date.now());
    tick();
    const timer = window.setInterval(tick, 500);
    return () => window.clearInterval(timer);
  }, []);

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
