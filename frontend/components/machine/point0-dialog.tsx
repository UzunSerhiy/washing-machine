'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCalibrationHome, getRollerReference } from '@/lib/calibration-api';

/** Shared read-only Point0 panel. Motion controls are intentionally not wired. */
export function Point0Dialog() {
  const [open, setOpen] = useState(false);
  const home = useQuery({
    queryKey: ['machine', 'home'],
    queryFn: getCalibrationHome,
    enabled: open,
    refetchInterval: 500,
    retry: false,
  });
  const sensor = useQuery({
    queryKey: ['machine', 'roller-reference'],
    queryFn: getRollerReference,
    enabled: open,
    refetchInterval: 500,
    retry: false,
  });

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="rounded-lg border px-4 py-2 font-medium">
        Point0 / HOME
      </button>
      {open && (
        <div role="presentation" className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <section role="dialog" aria-modal="true" aria-labelledby="point0-title" className="w-full max-w-lg space-y-4 rounded-xl border bg-background p-6 shadow-xl">
            <div className="flex items-center justify-between gap-3">
              <h2 id="point0-title" className="text-xl font-semibold">Установка Point0</h2>
              <button type="button" onClick={() => setOpen(false)} className="rounded border px-3 py-1">Закрыть</button>
            </div>
            <p className="text-sm text-muted-foreground">Общее окно для MANUAL, AUTO и CALIBRATION. На этом этапе доступна только диагностика; команды движения не отправляются.</p>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-3"><dt>HOME</dt><dd>{home.isError ? 'Ошибка запроса' : home.data?.state ?? 'Загрузка…'}</dd></div>
              <div className="flex justify-between gap-3"><dt>Датчик</dt><dd>{sensor.isError ? 'Ошибка запроса' : !sensor.data ? 'Загрузка…' : !sensor.data.connected ? 'Нет связи' : sensor.data.triggered ? 'Активен' : 'Не активен'}</dd></div>
              <div className="flex justify-between gap-3"><dt>Импульсы</dt><dd>{sensor.data?.pulses ?? '—'}</dd></div>
            </dl>
            {home.data?.error && <p role="alert" className="text-sm text-red-600">{home.data.error}</p>}
            <div className="grid grid-cols-3 gap-2">
              <button type="button" disabled className="rounded border p-3 opacity-50" title="Пока недоступно: требуется backend watchdog удержания">◀ Reverse</button>
              <button type="button" disabled className="rounded border p-3 opacity-50">Stop</button>
              <button type="button" disabled className="rounded border p-3 opacity-50" title="Пока недоступно: требуется backend watchdog удержания">Forward ▶</button>
            </div>
            <button type="button" disabled className="w-full rounded border p-3 opacity-50">Автодоводка до Point0 — пока недоступна</button>
            <p className="text-xs text-amber-600">Для движения с удержанием нужен серверный тайм-аут команд. Простое отпускание кнопки в браузере не гарантирует остановку при потере соединения.</p>
          </section>
        </div>
      )}
    </>
  );
}
