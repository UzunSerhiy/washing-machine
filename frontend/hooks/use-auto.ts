'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { getAutoSession, sendAutoCommand, selectAutoMaterial } from '@/lib/auto-api';

export function useAutoSession() {
  return useQuery({
    queryKey: ['auto-session'],
    queryFn: getAutoSession,
    refetchInterval: 300,
  });
}

export function useAutoCommand() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: sendAutoCommand,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['auto-session'] }),
        queryClient.invalidateQueries({ queryKey: ['machine'] }),
      ]);
    },
  });
}

export function useSelectAutoMaterial() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: selectAutoMaterial,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['auto-session'] }),
        queryClient.invalidateQueries({ queryKey: ['machine'] }),
      ]);
    },
  });
}
