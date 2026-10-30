"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { getCalibrationHome, getRollerReference } from "@/lib/calibration-api";

export function ManualHomeControl() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [frequency, setFrequency] = useState(5);
  const [message, setMessage] = useState<string | null>(null);
  const home = useQuery({ queryKey: ["machine", "home"], queryFn: getCalibrationHome, refetchInterval: 500, retry: false });
  const sensor = useQuery({ queryKey: ["machine", "roller-reference"], queryFn: getRollerReference, enabled: open, refetchInterval: 500, retry: false });
  const refresh = () => client.invalidateQueries({ queryKey: ["machine", "home"] });
  const start = useMutation({
    mutationFn: () => api.post("/api/machine/home", { position_confirmed: confirmed, frequency_hz: frequency }),
    onSuccess: () => { setMessage(null); setConfirmed(false); void refresh(); },
    onError: (error) => setMessage(error instanceof Error ? error.message : "Ошибка запуска HOME"),
  });
  const cancel = useMutation({
    mutationFn: () => api.post("/api/machine/home/cancel"),
    onSuccess: () => { setMessage(null); void refresh(); },
    onError: (error) => setMessage(error instanceof Error ? error.message : "Ошибка отмены HOME"),
  });
  const running = Boolean(home.data?.searching || home.data?.awaiting_stop_confirmation);
  const homed = home.isSuccess && home.data?.homed === true && !home.data?.faulted;
  const ready = home.isSuccess && sensor.isSuccess && sensor.data.connected &&
    !home.data.faulted && !running && !start.isPending && !cancel.isPending;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        className={`rounded-lg px-5 py-3 font-semibold text-white disabled:opacity-50 ${home.isPending || home.isError ? "bg-amber-600" : homed ? "bg-emerald-600" : "bg-red-600"}`}
      >
        {home.isPending || home.isError ? "Point0: нет данных" : homed ? "Point0 установлен ✓" : "Point0 не установлен — поиск нуля"}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation">
          <section role="dialog" aria-modal="true" aria-labelledby="manual-home-title" className="w-full max-w-lg space-y-4 rounded-xl border bg-background p-6 shadow-xl">
            <div className="flex items-center justify-between gap-3">
              <h2 id="manual-home-title" className="text-xl font-semibold">Установка Point0 / HOME</h2>
              <button type="button" onClick={() => setOpen(false)} className="rounded border px-3 py-1">Закрыть</button>
            </div>
            <p className={`rounded-lg px-3 py-2 text-sm font-semibold ${homed ? "bg-emerald-600/10 text-emerald-600" : "bg-red-600/10 text-red-600"}`}>
              {homed ? "Нулевое положение подтверждено" : running ? "Идёт поиск нуля" : "Нулевое положение не подтверждено"}
            </p>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-3"><dt>HOME</dt><dd>{home.isError ? "Ошибка запроса" : home.data?.state ?? "Загрузка…"}</dd></div>
              <div className="flex justify-between gap-3"><dt>Point0 подтверждён</dt><dd>{homed ? "Да" : "Нет"}</dd></div>
              <div className="flex justify-between gap-3"><dt>Блокировка HOME</dt><dd>{home.data?.faulted ? "Ошибка зафиксирована" : "Нет"}</dd></div>
              <div className="flex justify-between gap-3"><dt>Владелец роллера</dt><dd>{home.data?.roller_owner ?? "—"}</dd></div>
              <div className="flex justify-between gap-3"><dt>Датчик ESP32</dt><dd>{sensor.isError ? "Ошибка запроса" : !sensor.data ? "Загрузка…" : !sensor.data.connected ? "Нет связи" : sensor.data.triggered ? "Активен" : "Не активен"}</dd></div>
              <div className="flex justify-between gap-3"><dt>Импульсы</dt><dd>{sensor.data?.pulses ?? "—"}</dd></div>
            </dl>
            <label className="flex items-center gap-3 text-sm">Скорость поиска, Гц
              <input className="w-24 rounded border bg-background px-2 py-1" type="number" min={1} max={10} step={1} value={frequency} onChange={e => setFrequency(Number(e.target.value))} disabled={running} />
            </label>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} disabled={running} />
              Подтверждаю: вал остановлен, щётки остановлены, исходное положение позволяет обнаружить датчик за первый оборот.
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button type="button" className="rounded-lg bg-emerald-600 px-4 py-3 text-white disabled:opacity-50" disabled={!ready || !confirmed || !Number.isFinite(frequency) || frequency < 1 || frequency > 10} onClick={() => start.mutate()}>Поиск нуля</button>
              <button type="button" className="rounded-lg bg-red-600 px-4 py-3 text-white disabled:opacity-50" disabled={!running || cancel.isPending} onClick={() => cancel.mutate()}>Остановить поиск</button>
            </div>
            {(message || home.data?.error) && <p role="alert" className="text-sm text-red-600">{message || home.data?.error}</p>}
            <p className="text-xs text-muted-foreground">Ограничения backend: максимум 10 Гц, 60 секунд и 1,2 оборота. Программная отмена не заменяет физическую аварийную остановку.</p>
          </section>
        </div>
      )}
    </>
  );
}
