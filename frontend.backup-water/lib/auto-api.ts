import { api } from '@/lib/api';
import type { AutoCommand, AutoSession } from '@/types/auto';

export async function getAutoSession(): Promise<AutoSession> {
  const response = await api.get<AutoSession>('/api/machine/auto/session');

  return response.data;
}

export async function sendAutoCommand(command: AutoCommand): Promise<AutoSession> {
  const response = await api.post<AutoSession>(`/api/machine/auto/${command}`);

  return response.data;
}

export async function selectAutoMaterial(materialProfileId: number): Promise<void> {
  await api.post('/api/machine/mode/auto', {
    material_profile_id: materialProfileId,
  });
}
