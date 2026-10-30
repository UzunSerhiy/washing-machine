'use client';

import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

const tabs = [
  { href: '/manual', label: 'MANUAL', mode: 'manual' },
  { href: '/auto', label: 'AUTO', mode: 'auto' },
  { href: '/calibration', label: 'CALIBRATION', mode: 'calibration' },
] as const;

type Operation = { mode: string; running: boolean; paused: boolean; roller_running: boolean; brush_running: boolean };
type Calibration = { active: boolean };
type Auto = { status: string };

export function MachineNavigation() {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const operation = useQuery({ queryKey: ['machine', 'operation'], queryFn: async () => (await api.get<Operation>('/api/machine/operation')).data, refetchInterval: 1000 });
  const calibration = useQuery({ queryKey: ['machine', 'calibration', 'session'], queryFn: async () => (await api.get<Calibration>('/api/machine/calibration')).data, refetchInterval: 1000 });
  const auto = useQuery({ queryKey: ['machine', 'auto', 'session'], queryFn: async () => (await api.get<Auto>('/api/machine/auto/session')).data, refetchInterval: 1000 });
  const current = tabs.find(tab => pathname === tab.href || pathname.startsWith(`${tab.href}/`));
  const busy = Boolean(operation.data?.running || operation.data?.paused || operation.data?.roller_running || operation.data?.brush_running || calibration.data?.active || ['PREPARED', 'RUNNING', 'PAUSED'].includes(auto.data?.status ?? ''));
  const manual = useQuery({ queryKey: ['machine', 'manual', 'session'], queryFn: async () => (await api.get<{active: boolean}>('/api/machine/manual/session')).data, refetchInterval: 1000 });
  const ready = operation.isSuccess && calibration.isSuccess && auto.isSuccess && manual.isSuccess;
  const occupied = busy || manual.data?.active;

  return (
    <div className="space-y-2">
      <nav aria-label="Machine modes" className="grid grid-cols-3 gap-1 rounded-xl border bg-muted/50 p-1">
        {tabs.map(tab => {
          const active = current?.mode === tab.mode;
          return (
            <button key={tab.href} type="button" aria-current={active ? 'page' : undefined}
              className={`rounded-lg px-3 py-3 text-center text-sm font-semibold transition-colors sm:text-base ${active ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:bg-background/70 hover:text-foreground'}`}
              disabled={switching}
              onClick={async () => {
                setError(null);
                if (active) return;
                if (!ready) { setError('Нет подтверждённого состояния сессий. Переключение заблокировано.'); return; }
                if (occupied) { setError(`Сначала завершите активную сессию или остановите движение в ${current?.label ?? operation.data?.mode.toUpperCase()}.`); return; }
                setSwitching(true);
                try {
                  await api.post('/api/machine/mode/select', { mode: tab.mode });
                  await queryClient.invalidateQueries({ queryKey: ['machine', 'operation'] });
                  router.push(tab.href);
                } catch (err) {
                  const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
                  setError(detail || 'Не удалось выбрать режим.');
                } finally { setSwitching(false); }
              }}>
              {tab.label}
            </button>
          );
        })}
      </nav>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
