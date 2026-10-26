"use client";

import { useState } from "react";
import axios from "axios";

import { useMaterialProfiles } from "@/hooks/use-material-profiles";

import {
  useCalibrationSession,
  useAutoWindCalibration,
  useResumeCalibration,
  useNextCalibrationStep,
  useStartCalibration,
  useJogCalibration,
  useCalibrationAction,
  useMarkCalibrationPoint,
  useCompleteCalibration,
  useCancelCalibration,
  useStartCalibrationBrush,
  useStopCalibrationBrush,
  useCalibrationHome,
  useRollerReference,
  useStartCalibrationHome,
  useSaveCalibrationGeometry,
} from "@/hooks/use-calibration";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Slider } from "@/components/ui/slider";

function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string" ? detail : error.message;
  }

  return error instanceof Error ? error.message : "Unknown error";
}

function formatTurns(value: number | null | undefined) {
  return value == null ? "—" : value.toFixed(4);
}

const ROLLER_MAX_FREQUENCY_HZ = 50;

function percentToHz(percent: number): number {
  return (percent / 100) * ROLLER_MAX_FREQUENCY_HZ;
}

const BRUSH_MAX_FREQUENCY_HZ = 10;

function brushPercentToHz(percent: number): number {
  return (percent / 100) * BRUSH_MAX_FREQUENCY_HZ;
}

export default function CalibrationPage() {
  const [materialId, setMaterialId] = useState("");
  const [rollerSpeedPercent, setRollerSpeedPercent] = useState(10);
  const [brushSpeedPercent, setBrushSpeedPercent] = useState(30);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [positionConfirmed, setPositionConfirmed] = useState(false);

  const materialsQuery = useMaterialProfiles();
  const sessionQuery = useCalibrationSession();
  const homeQuery = useCalibrationHome();
  const sensorQuery = useRollerReference();
  const startHome = useStartCalibrationHome();

  const start = useStartCalibration();
  const nextStep = useNextCalibrationStep();
  const autoWind = useAutoWindCalibration();
  const resume = useResumeCalibration();
  const jog = useJogCalibration();
  const action = useCalibrationAction();
  const mark = useMarkCalibrationPoint();
  const complete = useCompleteCalibration();
  const cancel = useCancelCalibration();

  const session = sessionQuery.data;
  const active = session?.active === true;
  const homingActive = homeQuery.data?.state === "searching";

  const startBrush = useStartCalibrationBrush();
  const stopBrush = useStopCalibrationBrush();

  const [finalDiameter, setFinalDiameter] = useState("");
  const saveGeometry = useSaveCalibrationGeometry();

  const busy =
    start.isPending ||
    nextStep.isPending ||
    autoWind.isPending ||
    resume.isPending ||
    jog.isPending ||
    action.isPending ||
    mark.isPending ||
    complete.isPending ||
    cancel.isPending ||
    startBrush.isPending ||
    stopBrush.isPending ||
    startHome.isPending ||
    saveGeometry.isPending;

  const canComplete =
    active &&
    !busy &&
    !session?.running &&
    !session?.brush_running &&
    session?.material_start_turns != null &&
    session?.material_end_turns != null &&
    session?.washing_stop_turns != null &&
    session?.water_start_turns != null &&
    session?.stage === "washing_stop" &&
    !session?.saved;

  async function execute(fn: () => Promise<unknown>) {
    setError(null);
    setMessage(null);

    try {
      await fn();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function handleStart() {
    const id = Number(materialId);

    if (!Number.isInteger(id) || id <= 0) {
      setError("Выбери материал");
      return;
    }

    execute(() => start.mutateAsync(id));
  }

  function handleJog(direction: "forward" | "reverse") {
    if (
      !Number.isFinite(rollerSpeedPercent) ||
      rollerSpeedPercent <= 0 ||
      rollerSpeedPercent > 100
    ) {
      setError("Скорость должна быть от 1 до 100%");
      return;
    }

    const frequencyHz = percentToHz(rollerSpeedPercent);

    execute(() =>
      jog.mutateAsync({
        direction,
        frequencyHz,
        brushFrequencyHz:
          stage === "water_start" && direction === "reverse"
            ? brushPercentToHz(brushSpeedPercent)
            : undefined,
      }),
    );
  }

  function handleComplete() {
    execute(async () => {
      await complete.mutateAsync();
      setMessage("Калибровка сохранена в PostgreSQL");
    });
  }

  function handleCancel() {
    execute(() => cancel.mutateAsync());
  }

  const stage = session?.stage;

  const steps = [
    { key: "set_zero", label: "Установка нуля" },
    { key: "material_start", label: "Начало материала" },
    { key: "material_end", label: "Конец материала" },
    { key: "water_start", label: "Точка включения воды" },
    { key: "ready_to_unwind", label: "Автоматическая отмотка" },
    { key: "washing_stop", label: "Конец мойки" },
    { key: "rewind_complete", label: "Автонамотка завершена" },
  ];

  const currentStepIndex = steps.findIndex((step) => step.key === stage);

  const canJog =
    active &&
    !homingActive &&
    !busy &&
    [
      "set_zero",
      "material_start",
      "material_end",
      "water_start",
      "washing_stop",
    ].includes(stage ?? "") &&
    !session?.saved &&
    !session?.running &&
    !session?.auto_mode;

  const atUpper =
    stage === "water_start"
      ? session?.material_end_turns
      : stage === "washing_stop"
        ? session?.material_start_turns
        : null;
  const atLower =
    stage === "water_start"
      ? session?.material_start_turns
      : stage === "washing_stop"
        ? 0
        : null;
  const canForward =
    canJog &&
    (atUpper == null || (session?.position_turns ?? 0) < atUpper - 0.000001);
  const canReverse =
    canJog &&
    (atLower == null || (session?.position_turns ?? 0) > atLower + 0.000001);

  const currentAction = {
    set_zero: {
      label: "Установить ноль",
      description: "Установить текущую позицию как нулевую",
    },
    material_start: {
      label: "Зафиксировать начало материала",
      description: "Сохранить текущую позицию начала материала",
    },
    material_end: {
      label: "Зафиксировать конец материала",
      description: "Сохранить текущую позицию конца материала",
    },
    water_start: {
      label: "Зафиксировать Water Start",
      description:
        "Первый Reverse запускает роллер и щётки. Pause останавливает оба. Затем точная настройка Forward/Reverse без щёток.",
    },
    washing_stop: {
      label: "Зафиксировать конец мойки",
      description:
        "Установи позицию между нулём и началом материала и зафиксируй.",
    },
    ready_to_unwind: {
      label: "Авторазмотка до Material Start",
      description:
        "Роллер и щётки работают; при достижении Material Start остановятся.",
    },
    rewind_complete: {
      label: "Автонамотка завершена",
      description: "Роллер остановлен на Material End.",
    },
  }[stage ?? "set_zero"];

  const points = [
    {
      key: "zero",
      label: "Нулевая позиция",
      value: 0,
      ready: active && stage !== "set_zero",
    },
    {
      key: "material_start",
      label: "Начало материала",
      value: session?.material_start_turns,
      ready: session?.material_start_turns != null,
    },
    {
      key: "material_end",
      label: "Конец материала",
      value: session?.material_end_turns,
      ready: session?.material_end_turns != null,
    },
    {
      key: "water_start",
      label: "Включение воды",
      value: session?.water_start_turns,
      ready: session?.water_start_turns != null,
    },
    {
      key: "washing_stop",
      label: "Конец мойки",
      value: session?.washing_stop_turns,
      ready: session?.washing_stop_turns != null,
    },
  ];

  async function handleCurrentAction() {
    if (!active || busy || session?.running) return;

    switch (stage) {
      case "set_zero":
        await execute(() => action.mutateAsync("reset-position"));
        break;

      case "material_start":
        await execute(() => mark.mutateAsync({ point: "material_start" }));
        break;

      case "material_end":
        await execute(() => mark.mutateAsync({ point: "material_end" }));
        break;

      case "water_start":
        await execute(() =>
          mark.mutateAsync({
            point: "water_start",
            brushFrequencyHz: brushPercentToHz(brushSpeedPercent),
          }),
        );
        break;
      case "ready_to_unwind":
        setError(
          "Авторазмотка запускается автоматически после фиксации Water Start",
        );
        break;
      case "washing_stop":
        await execute(() => mark.mutateAsync({ point: "washing_stop" }));
        break;
    }
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Калибровка</h1>
        <p className="text-muted-foreground">
          Настройка положения ролика и контрольных точек
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Материал</CardTitle>
        </CardHeader>

        <CardContent className="flex flex-wrap items-center gap-3">
          <Select
            value={materialId}
            onValueChange={(value) => setMaterialId(value ?? "")}
            disabled={active || busy}
          >
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Выбери материал" />
            </SelectTrigger>

            <SelectContent>
              {(materialsQuery.data ?? []).map((material) => (
                <SelectItem key={material.id} value={String(material.id)}>
                  {material.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            onClick={handleStart}
            disabled={active || busy || !materialId}
          >
            Начать калибровку
          </Button>

          {active && (
            <span className="text-sm text-muted-foreground">
              Активный материал: {session?.material_profile_id}
            </span>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Этапы калибровки</CardTitle>
        </CardHeader>

        <CardContent className="space-y-3">
          {steps.map((step, index) => (
            <div
              key={step.key}
              className={`rounded-lg border p-3 ${
                index === currentStepIndex ? "border-primary bg-primary/5" : ""
              }`}
            >
              <span className="mr-3">{index + 1}.</span>
              {step.label}
              {index < currentStepIndex && (
                <span className="ml-3 text-green-600">✓</span>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Положение ролика</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="text-4xl font-mono font-semibold">
            {formatTurns(session?.position_turns)}
            <span className="ml-2 text-base font-normal">оборотов</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <p className="text-sm text-muted-foreground">Состояние</p>
              <p>
                {!active
                  ? "Неактивна"
                  : session?.running
                    ? "Вращение"
                    : session?.paused
                      ? "Пауза"
                      : "Остановлено"}
              </p>
            </div>

            <div>
              <p className="text-sm text-muted-foreground">Направление</p>
              <p>{session?.direction ?? "—"}</p>
            </div>

            <div>
              <p className="text-sm text-muted-foreground">Частота</p>
              <p>{session?.frequency_hz ?? 0} Hz</p>
            </div>
          </div>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {currentAction.description}
            </p>

            <Button
              className="w-full"
              size="lg"
              disabled={
                !active ||
                busy ||
                session?.running ||
                !!session?.saved ||
                stage === "ready_to_unwind" ||
                stage === "rewind_complete" ||
                (stage === "water_start" &&
                  (session?.brush_running ||
                    (session?.position_turns ?? 0) >=
                      (session?.material_end_turns ?? 0)))
              }
              onClick={handleCurrentAction}
            >
              {currentAction.label}
            </Button>
          </div>
        </CardContent>
      </Card>

      {active && stage === "set_zero" && (
        <Card>
          <CardHeader>
            <CardTitle>Автоматический поиск нуля</CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-1 text-sm">
              <p>
                Датчик:{" "}
                {!sensorQuery.data?.connected
                  ? "Нет связи"
                  : sensorQuery.data.triggered
                    ? "Нажат"
                    : "Отпущен"}
              </p>
              <p>Поиск: {homeQuery.data?.state ?? "—"}</p>
              {homeQuery.data?.error && (
                <p className="text-red-600">{homeQuery.data.error}</p>
              )}
            </div>

            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={positionConfirmed}
                disabled={homingActive}
                onChange={(event) => setPositionConfirmed(event.target.checked)}
              />
              <span>
                Подтверждаю, что вал вручную установлен в диапазоне от 0 до 1
                оборота, а микрик отпущен.
              </span>
            </label>

            <Button
              className="w-full"
              disabled={
                busy ||
                homingActive ||
                !!session?.running ||
                !!session?.brush_running ||
                !positionConfirmed ||
                !sensorQuery.data?.connected ||
                !!sensorQuery.data?.triggered
              }
              onClick={() =>
                execute(async () => {
                  await startHome.mutateAsync();
                  setPositionConfirmed(false);
                })
              }
            >
              {homingActive ? "Поиск нуля..." : "Найти ноль (10 Hz)"}
            </Button>

            <p className="text-xs text-muted-foreground">
              Поиск выполняется в обратном направлении. Для остановки используй
              Stop ниже. В режиме REAL запуск HOME пока заблокирован сервером;
              эта кнопка предназначена только для FAKE-тестирования.
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Управление роликом</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span>Скорость ролика</span>
              <span className="font-mono font-semibold">
                {rollerSpeedPercent}%
              </span>
            </div>

            <Slider
              min={1}
              max={100}
              step={1}
              value={[rollerSpeedPercent]}
              onValueChange={(value) =>
                setRollerSpeedPercent(
                  typeof value === "number" ? value : (value[0] ?? 10),
                )
              }
              disabled={!active || busy}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <Button disabled={!canReverse} onClick={() => handleJog("reverse")}>
              ◀ Reverse
            </Button>

            <Button disabled={!canForward} onClick={() => handleJog("forward")}>
              Forward ▶
            </Button>

            <Button
              variant="outline"
              disabled={!active || busy || !session?.running}
              onClick={() => execute(() => action.mutateAsync("pause"))}
            >
              Pause
            </Button>

            <Button
              variant="destructive"
              disabled={!active || (busy && !homingActive)}
              onClick={() => execute(() => action.mutateAsync("stop"))}
            >
              Stop
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Управление щётками</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span>Скорость щёток</span>
              <span className="font-mono font-semibold">
                {brushSpeedPercent}%
              </span>
            </div>

            <Slider
              min={0}
              max={100}
              step={1}
              value={[brushSpeedPercent]}
              onValueChange={(value) =>
                setBrushSpeedPercent(
                  typeof value === "number" ? value : (value[0] ?? 30),
                )
              }
              disabled={!active || busy}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              disabled={
                !active ||
                busy ||
                homingActive ||
                brushSpeedPercent <= 0 ||
                !!session?.saved ||
                ["water_start", "ready_to_unwind"].includes(stage ?? "")
              }
              onClick={() =>
                execute(() =>
                  startBrush.mutateAsync(brushPercentToHz(brushSpeedPercent)),
                )
              }
            >
              Запустить щётки
            </Button>

            <Button
              variant="outline"
              disabled={
                !active ||
                busy ||
                !session?.brush_running ||
                ["water_start", "ready_to_unwind"].includes(stage ?? "")
              }
              onClick={() => execute(() => stopBrush.mutateAsync())}
            >
              Остановить щётки
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Контрольные точки</CardTitle>
        </CardHeader>

        <CardContent className="space-y-3">
          {points.map((point) => (
            <div
              key={point.key}
              className="flex items-center justify-between gap-3 rounded-lg border p-4"
            >
              <div className="space-y-1">
                <p className="font-medium">{point.label}</p>

                <p className="font-mono text-sm text-muted-foreground">
                  {point.ready
                    ? `${formatTurns(point.value)} оборотов`
                    : "Не установлена"}
                </p>
              </div>

              <div
                className={
                  point.ready
                    ? "flex items-center gap-2 text-green-600"
                    : "flex items-center gap-2 text-muted-foreground"
                }
              >
                <span
                  className={
                    point.ready
                      ? "h-2.5 w-2.5 rounded-full bg-green-500"
                      : "h-2.5 w-2.5 rounded-full bg-muted-foreground/40"
                  }
                />

                <span className="text-sm font-semibold">
                  {point.ready ? "READY" : "PENDING"}
                </span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Завершение калибровки</CardTitle>
        </CardHeader>

        <CardContent className="flex flex-wrap gap-3">
          {session?.saved && stage !== "rewind_complete" && (
            <Button
              disabled={busy || !!session?.running || !!session?.auto_mode}
              onClick={() => execute(() => autoWind.mutateAsync())}
            >
              Автонамотка до Material End (макс. скорость)
            </Button>
          )}
          {session?.auto_mode === "paused" && (
            <Button
              disabled={busy}
              onClick={() =>
                execute(() =>
                  resume.mutateAsync(brushPercentToHz(brushSpeedPercent)),
                )
              }
            >
              Продолжить автоматическое движение
            </Button>
          )}
          <Button disabled={!canComplete} onClick={handleComplete}>
            Сохранить калибровку
          </Button>

          <Button
            variant="outline"
            disabled={!active || busy}
            onClick={handleCancel}
          >
            Отменить
          </Button>
        </CardContent>
      </Card>

      {active && session?.saved && stage === "rewind_complete" && (
        <Card>
          <CardHeader>
            <CardTitle>Геометрия материала</CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Автонамотка завершена. Измерь наружный диаметр рулона и введи его
              в миллиметрах.
            </p>

            <label className="block space-y-2">
              <span className="text-sm font-medium">
                Наружный диаметр рулона, мм
              </span>
              <input
                type="number"
                min="0"
                step="0.1"
                value={finalDiameter}
                onChange={(event) => setFinalDiameter(event.target.value)}
                placeholder="Например, 260"
                className="w-full rounded-md border bg-background px-3 py-2"
              />
            </label>

            <Button
              className="w-full"
              disabled={
                busy ||
                !!session?.running ||
                !!session?.brush_running ||
                session?.auto_mode != null ||
                !finalDiameter.trim() ||
                !Number.isFinite(Number(finalDiameter)) ||
                Number(finalDiameter) <= 0
              }
              onClick={() =>
                execute(async () => {
                  const result = await saveGeometry.mutateAsync(
                    Number(finalDiameter),
                  );

                  setMessage(
                    `Геометрия сохранена. Толщина материала: ${result.material_thickness_mm.toFixed(4)} мм`,
                  );
                })
              }
            >
              Рассчитать толщину и сохранить
            </Button>
          </CardContent>
        </Card>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-600"
        >
          {error}
        </div>
      )}

      {message && (
        <div className="rounded-lg border p-4 text-sm">{message}</div>
      )}

      {sessionQuery.isError && !active && (
        <p className="text-sm text-muted-foreground">
          Активной сессии калибровки нет.
        </p>
      )}
    </main>
  );
}
