"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { evaluateManualMotionDiagnostics, evaluateMotionUiDiagnostics } from "@/lib/motion-ui-diagnostics.mjs";

export interface DriveReadiness {
  drive_id: number;
  connected: boolean;
  status: number | null;
  frequency_hz: number | null;
  fault: number | null;
  reasons: string[];
}

export interface ReadinessSnapshot {
  drives: DriveReadiness[];
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

  return evaluateMotionUiDiagnostics(now, readiness, fault);
}

// Command-specific UI hints; backend and physical interlocks remain authoritative.
export function useManualMotionDiagnostics() {
  const readiness = useMachineReadiness();
  const fault = useMachineMotionFault();
  const [now, setNow] = useState(0);
  useEffect(() => {
    const tick = () => setNow(Date.now());
    tick();
    const timer = window.setInterval(tick, 500);
    return () => window.clearInterval(timer);
  }, []);
  return evaluateManualMotionDiagnostics(now, readiness, fault);
}
