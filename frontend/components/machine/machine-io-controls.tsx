"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Droplets, Lightbulb } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Device = "light" | "water";
type MachineMode = "manual" | "auto" | "calibration";

type IOStatus = {
  connected: boolean;
  watchdog_alive: boolean;
  io_ready: boolean;
  water_switch: boolean;
  light_switch: boolean;
  water_output: boolean;
  light_output: boolean;
  water_switch_changes: number;
  light_switch_changes: number;
  generation: number;
  boot_id: number | null;
};

type MachineOperation = {
  mode: MachineMode;
  material_profile_id: number | null;
  running: boolean;
  paused: boolean;
};

type SelectableMode = "manual" | "auto" | "calibration";

const ioQueryKey = ["machine", "io", "diagnostics"];
const modeQueryKey = ["machine", "operation"];

async function fetchIOStatus(): Promise<IOStatus> {
  const { data } = await api.get<IOStatus>("/api/machine/io/diagnostics");
  return data;
}

async function setIOOutput(device: Device, enabled: boolean): Promise<void> {
  await api.put(`/api/machine/io/${device}`, { enabled });
}

async function fetchMachineMode(): Promise<MachineOperation> {
  const { data } = await api.get<MachineOperation>("/api/machine/operation");
  return data;
}

async function changeMachineMode(
  mode: SelectableMode,
  materialProfileId: number | null,
): Promise<MachineOperation> {
  if (mode === "manual") {
    const { data } = await api.post<MachineOperation>(
      "/api/machine/mode/manual",
    );
    return data;
  }

  if (materialProfileId === null) {
    throw new Error(
      "Для AUTO и CALIBRATION необходимо выбрать профиль материала.",
    );
  }

  const { data } = await api.post<MachineOperation>(
    `/api/machine/mode/${mode}`,
    { material_profile_id: materialProfileId },
  );

  return data;
}

function describeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string" ? detail : error.message;
  }
  return error instanceof Error ? error.message : "Неизвестная ошибка";
}

export function MachineIOControls() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: ioQueryKey,
    queryFn: fetchIOStatus,
    refetchInterval: 300,
    staleTime: 0,
    retry: 1,
  });

  const modeQuery = useQuery({
    queryKey: modeQueryKey,
    queryFn: fetchMachineMode,
    refetchInterval: 1000,
    staleTime: 0,
    retry: 1,
  });

  const command = useMutation({
    mutationFn: ({ device, enabled }: { device: Device; enabled: boolean }) =>
      setIOOutput(device, enabled),

    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ioQueryKey });
    },

    onError: (err) => {
      setError(describeError(err));
    },
  });

  const modeCommand = useMutation({
    mutationFn: (mode: SelectableMode) =>
      changeMachineMode(mode, modeQuery.data?.material_profile_id ?? null),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["machine"],
      });
    },

    onError: (err) => {
      setError(describeError(err));
    },
  });

  const status = statusQuery.data;
  const operation = modeQuery.data;

  const available =
    !statusQuery.isError &&
    status?.connected === true &&
    status.watchdog_alive === true &&
    status.io_ready === true;

  const modeBusy =
    modeCommand.isPending ||
    modeQuery.isLoading ||
    modeQuery.isError ||
    !operation ||
    operation.running ||
    operation.paused;

  function handleToggle(device: Device) {
    if (!available || command.isPending || !status) return;

    setError(null);

    const enabled =
      device === "light" ? status.light_output : status.water_output;

    command.mutate({ device, enabled: !enabled });
  }

  function handleModeChange(mode: SelectableMode) {
    if (modeBusy || operation?.mode === mode) return;

    setError(null);
    modeCommand.mutate(mode);
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Управление машиной</CardTitle>
        <p className="text-sm text-muted-foreground">
          Режим работы, освещение и подача воды
        </p>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Режим работы</span>

            <span className="text-xs font-semibold text-muted-foreground">
              {modeQuery.isError
                ? "НЕТ СВЯЗИ"
                : (operation?.mode?.toUpperCase() ?? "ЗАГРУЗКА")}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {(
              [
                { mode: "manual", label: "MANUAL" },
                { mode: "auto", label: "AUTO" },
                { mode: "calibration", label: "CALIBRATION" },
              ] as const
            ).map(({ mode, label }) => (
              <Button
                key={mode}
                type="button"
                variant={operation?.mode === mode ? "default" : "outline"}
                disabled={modeBusy}
                onClick={() => handleModeChange(mode)}
                aria-pressed={operation?.mode === mode}
                className="h-14 px-2 text-xs sm:text-sm"
              >
                {label}
              </Button>
            ))}
          </div>
          {(operation?.running || operation?.paused) && (
            <p className="text-xs text-muted-foreground">
              Переключение заблокировано до завершения текущей операции.
            </p>
          )}
        </div>

        <div className="border-t pt-4 space-y-3">
          <p className="text-sm text-muted-foreground">
            {available
              ? "ESP32 подключена · управление доступно"
              : "Нет подтверждённой связи с ESP32"}
          </p>

          <div className="grid gap-3 sm:grid-cols-2">
            {[
              {
                device: "light" as const,
                label: "Свет",
                Icon: Lightbulb,
                enabled: status?.light_output,
              },
              {
                device: "water" as const,
                label: "Вода",
                Icon: Droplets,
                enabled: status?.water_output,
              },
            ].map(({ device, label, Icon, enabled }) => (
              <Button
                key={device}
                type="button"
                variant={available && enabled ? "default" : "outline"}
                disabled={!available || command.isPending}
                onClick={() => handleToggle(device)}
                className="h-20 flex-col gap-1"
                aria-pressed={available ? Boolean(enabled) : undefined}
              >
                <Icon className="size-5" />
                <span>
                  {label}: {available ? (enabled ? "ON" : "OFF") : "НЕТ СВЯЗИ"}
                </span>
              </Button>
            ))}
          </div>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}

        {statusQuery.isError && (
          <p role="alert" className="text-sm text-red-600">
            Не удалось получить состояние выходов.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
