'use client';
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';

export function ManualSessionControl() {
  const qc = useQueryClient();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const session = useQuery({ queryKey: ['machine', 'manual', 'session'], queryFn: async () => (await api.get<{active: boolean}>('/api/machine/manual/session')).data, refetchInterval: 1000 });
  async function change(action: 'start' | 'end') {
    setError(null); setPending(true);
    try {
      await api.post(`/api/machine/manual/session/${action}`);
      await qc.invalidateQueries({ queryKey: ['machine', 'manual', 'session'] });
    } catch (e) {
      setError((e as {response?: {data?: {detail?: string}}}).response?.data?.detail || 'Не удалось изменить сессию');
    } finally { setPending(false); }
  }
  return <section className="rounded-xl border bg-card p-4 space-y-3">
    <p className="font-semibold">Сессия MANUAL: {session.data?.active ? 'активна' : 'не начата'}</p>
    <Button disabled={pending || !session.isSuccess || session.data?.active} onClick={() => change('start')}>Начать сессию</Button>{' '}
    <Button variant="outline" disabled={pending || !session.data?.active} onClick={() => change('end')}>Завершить сессию</Button>
    {error && <p role="alert" className="text-red-600 text-sm">{error}</p>}
  </section>;
}
