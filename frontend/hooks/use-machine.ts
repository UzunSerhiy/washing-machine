'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Machine, MachineOperation } from '@/types/machine';

export function useMachine() {
  return useQuery({
    queryKey: ['machine'],
    queryFn: async () => {
      const { data } = await api.get<Machine>('/api/machine');
      return data;
    },
    refetchInterval: 1000,
  });
}

export function useMachineOperation() {
  return useQuery({
    queryKey: ['machine', 'operation'],
    queryFn: async () => {
      const { data } = await api.get<MachineOperation>('/api/machine/operation');
      return data;
    },
    refetchInterval: 1000,
  });
}
