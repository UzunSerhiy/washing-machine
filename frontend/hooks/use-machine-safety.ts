"use client";

import { useQuery } from "@tanstack/react-query";
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
