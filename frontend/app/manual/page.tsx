'use client';

import { useState } from 'react';
import { Play, Square, RotateCcw, AlertCircle } from 'lucide-react';

import { useMachineOperation } from '@/hooks/use-machine';
import { useManualControl } from '@/hooks/use-manual-control';

export default function ManualPage() {
  const { data: operation, isPending, isError } = useMachineOperation();

  const { sendCommand, setSpeed, commandPending, speedPending } = useManualControl();

  const [rollerSpeed, setRollerSpeed] = useState(30);
  const [brushSpeed, setBrushSpeed] = useState(50);
  const [error, setError] = useState<string | null>(null);

  const busy = commandPending || speedPending;
  const manualMode = operation?.mode === 'manual';

  async function handleCommand(
    command: 'roller/forward' | 'roller/reverse' | 'roller/stop' | 'brush/start' | 'brush/stop',
  ) {
    setError(null);

    try {
      if (command === 'roller/forward' || command === 'roller/reverse') {
        await setSpeed({ drive: 'roller', speed: rollerSpeed });
      }

      if (command === 'brush/start') {
        await setSpeed({ drive: 'brush', speed: brushSpeed });
      }

      await sendCommand(command);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }
  async function handleSpeed(drive: 'roller' | 'brush', speed: number) {
    setError(null);

    try {
      await setSpeed({ drive, speed });
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  if (isPending) {
    return <main className="p-8">Loading machine...</main>;
  }

  if (isError) {
    return <main className="p-8 text-red-500">Cannot load machine state</main>;
  }

  return (
    <main className="min-h-screen p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-8">
        <header>
          <h1 className="text-3xl font-bold">Manual Control</h1>
          <p className="text-muted-foreground">Direct machine control through FastAPI</p>
        </header>

        {!manualMode && (
          <div className="rounded-lg border border-amber-500 p-4 text-amber-600">
            Manual control is unavailable in {operation.mode.toUpperCase()} mode.
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-lg border border-red-500 p-4 text-red-500"
          >
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="space-y-5 rounded-xl border bg-card p-6">
            <h2 className="text-xl font-semibold">Roller</h2>

            <p className="text-sm text-muted-foreground">
              Status: {operation.roller_running ? 'RUNNING' : 'STOPPED'}
            </p>

            <div className="space-y-3">
              <label className="flex justify-between">
                <span>Speed</span>
                <span>{rollerSpeed}%</span>
              </label>

              <input
                type="range"
                min={0}
                max={100}
                value={rollerSpeed}
                onChange={(e) => setRollerSpeed(Number(e.target.value))}
                disabled={!manualMode || busy}
                className="w-full"
              />

              <button
                onClick={() => handleSpeed('roller', rollerSpeed)}
                disabled={!manualMode || busy}
                className="w-full rounded-lg border p-3 disabled:opacity-50"
              >
                Apply Speed
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => handleCommand('roller/forward')}
                disabled={!manualMode || busy}
                className="rounded-lg bg-emerald-600 p-3 text-white disabled:opacity-50"
              >
                <Play className="mx-auto mb-1" />
                Forward
              </button>

              <button
                onClick={() => handleCommand('roller/reverse')}
                disabled={!manualMode || busy}
                className="rounded-lg bg-blue-600 p-3 text-white disabled:opacity-50"
              >
                <RotateCcw className="mx-auto mb-1" />
                Reverse
              </button>

              <button
                onClick={() => handleCommand('roller/stop')}
                disabled={!manualMode || busy}
                className="rounded-lg bg-red-600 p-3 text-white disabled:opacity-50"
              >
                <Square className="mx-auto mb-1" />
                Stop
              </button>
            </div>
          </section>

          <section className="space-y-5 rounded-xl border bg-card p-6">
            <h2 className="text-xl font-semibold">Brushes</h2>

            <p className="text-sm text-muted-foreground">
              Status: {operation.brush_running ? 'RUNNING' : 'STOPPED'}
            </p>

            <div className="space-y-3">
              <label className="flex justify-between">
                <span>Speed</span>
                <span>{brushSpeed}%</span>
              </label>

              <input
                type="range"
                min={0}
                max={100}
                value={brushSpeed}
                onChange={(e) => setBrushSpeed(Number(e.target.value))}
                disabled={!manualMode || busy}
                className="w-full"
              />

              <button
                onClick={() => handleSpeed('brush', brushSpeed)}
                disabled={!manualMode || busy}
                className="w-full rounded-lg border p-3 disabled:opacity-50"
              >
                Apply Speed
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleCommand('brush/start')}
                disabled={!manualMode || busy}
                className="rounded-lg bg-emerald-600 p-3 text-white disabled:opacity-50"
              >
                <Play className="mx-auto mb-1" />
                Start
              </button>

              <button
                onClick={() => handleCommand('brush/stop')}
                disabled={!manualMode || busy}
                className="rounded-lg bg-red-600 p-3 text-white disabled:opacity-50"
              >
                <Square className="mx-auto mb-1" />
                Stop
              </button>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

function getErrorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;

    if (response?.data?.detail) {
      return response.data.detail;
    }
  }

  return error instanceof Error ? error.message : 'Unknown error';
}
