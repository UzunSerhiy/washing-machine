import { api } from '@/lib/api';
import type { MachineOperation } from '@/types/machine';

export type ManualCommand =
  | 'roller/forward'
  | 'roller/reverse'
  | 'roller/stop'
  | 'brush/start'
  | 'brush/stop';

export async function sendManualCommand(command: ManualCommand): Promise<MachineOperation> {
  const { data } = await api.post<MachineOperation>(`/api/machine/manual/${command}`);

  return data;
}

export async function setManualSpeed(
  drive: 'roller' | 'brush',
  speedPercent: number,
): Promise<MachineOperation> {
  const { data } = await api.put<MachineOperation>(`/api/machine/manual/${drive}/speed`, {
    speed_percent: speedPercent,
  });

  return data;
}
