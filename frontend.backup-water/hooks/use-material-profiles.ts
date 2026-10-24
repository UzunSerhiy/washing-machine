'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { MaterialProfile } from '@/types/material-profile';

async function getMaterialProfiles(): Promise<MaterialProfile[]> {
  const response = await api.get<MaterialProfile[]>('/api/material-profiles');

  return response.data;
}

export function useMaterialProfiles() {
  return useQuery({
    queryKey: ['material-profiles'],
    queryFn: getMaterialProfiles,
    staleTime: 60_000,
  });
}
