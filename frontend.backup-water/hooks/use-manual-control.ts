'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { sendManualCommand, setManualSpeed, type ManualCommand } from '@/lib/machine-api';

export function useManualControl() {
  const queryClient = useQueryClient();

  const commandMutation = useMutation({
    mutationFn: (command: ManualCommand) => sendManualCommand(command),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['machine'],
      });
    },
  });

  const speedMutation = useMutation({
    mutationFn: ({ drive, speed }: { drive: 'roller' | 'brush'; speed: number }) =>
      setManualSpeed(drive, speed),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['machine'],
      });
    },
  });

  return {
    sendCommand: commandMutation.mutateAsync,
    setSpeed: speedMutation.mutateAsync,
    commandPending: commandMutation.isPending,
    speedPending: speedMutation.isPending,
  };
}
