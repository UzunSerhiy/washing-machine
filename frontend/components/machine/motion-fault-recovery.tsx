"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Fault = { latched: boolean; reason: string | null; recovery_available: boolean; recovery_note: string; diagnostic_only: boolean };

function errorText(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === "string") return response.data.detail;
  }
  return error instanceof Error ? error.message : "Не удалось подтвердить снятие блокировки";
}

export function MotionFaultRecovery() {
  const client = useQueryClient();
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const fault = useQuery({
    queryKey: ["machine", "motion-fault"],
    queryFn: async () => (await api.get<Fault>("/api/machine/motion-fault")).data,
    refetchInterval: 1000,
    retry: false,
    staleTime: 0,
  });
  const acknowledge = useMutation({
    mutationFn: async () => (await api.post("/api/machine/motion-fault/acknowledge", { operator_confirmed_stopped: true })).data,
    onSuccess: async () => {
      setConfirmed(false);
      setMessage("Подтверждение принято. Повторно проверяем состояние машины. Автоматический запуск не выполняется.");
      await Promise.all([
        client.invalidateQueries({ queryKey: ["machine", "motion-fault"] }),
        client.invalidateQueries({ queryKey: ["machine", "readiness"] }),
        client.invalidateQueries({ queryKey: ["machine", "operation"] }),
      ]);
    },
    onError: (error) => setMessage(`Блокировка не снята: ${errorText(error)}`),
  });

  if (!fault.data?.latched && !fault.isError) return null;
  return (
    <section className="space-y-3 rounded-xl border border-amber-500 p-4" aria-label="Снятие программной блокировки">
      <h2 className="text-lg font-semibold">Программная блокировка движения</h2>
      <p className="text-sm">{fault.data?.reason ?? "Не удалось получить состояние блокировки"}</p>
      <p className="text-sm text-muted-foreground">Сброс не заменяет аппаратный E-STOP и RESET. Движение не запускается автоматически.</p>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" checked={confirmed} onChange={(e) => { setConfirmed(e.target.checked); setMessage(null); }} disabled={!fault.data?.recovery_available || acknowledge.isPending} />
        <span>Подтверждаю: все механизмы физически остановлены, зона движения свободна, E-STOP отпущен и аппаратный RESET частотников выполнен.</span>
      </label>
      <button type="button" className="rounded-lg border px-4 py-2 disabled:opacity-50" disabled={!confirmed || !fault.data?.recovery_available || fault.isError || acknowledge.isPending} onClick={() => { setMessage(null); acknowledge.mutate(); }}>
        {acknowledge.isPending ? "Проверка остановки…" : "Подтвердить остановку и снять блокировку"}
      </button>
      {!fault.data?.recovery_available && <p className="text-sm text-amber-700">Восстановление сейчас недоступно. Проверьте backend и состояние оборудования.</p>}
      {message && <p role="status" className="text-sm">{message}</p>}
    </section>
  );
}
