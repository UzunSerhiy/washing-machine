'use client';

import { Activity, AlertCircle, Loader2 } from 'lucide-react';
import { DriveCard } from '@/components/machine/drive-card';
import { useMachine, useMachineOperation } from '@/hooks/use-machine';
import Link from 'next/link';

export default function DashboardPage() {
  const machineQuery = useMachine();
  const operationQuery = useMachineOperation();

  if (machineQuery.isPending || operationQuery.isPending) {
    return (
      <main className="flex min-h-screen items-center justify-center gap-3">
        <Loader2 className="animate-spin" />
        Loading machine...
      </main>
    );
  }

  if (machineQuery.isError || operationQuery.isError) {
    return (
      <main className="flex min-h-screen items-center justify-center gap-3 text-red-500">
        <AlertCircle />
        Cannot connect to FastAPI
      </main>
    );
  }

  const machine = machineQuery.data;
  const operation = operationQuery.data;

  return (
    <main className="min-h-screen bg-background p-6 md:p-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">{machine.name}</h1>
            <p className="text-muted-foreground">Industrial Washing Machine Control</p>
          </div>

          <Link href="/manual" className="rounded-lg border px-4 py-2 hover:bg-accent">
            Manual Control
          </Link>

          <div className="flex items-center gap-2 rounded-lg border px-4 py-2">
            <Activity size={18} className="text-emerald-500" />
            <span>API Connected</span>
          </div>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <InfoCard title="Mode" value={operation.mode.toUpperCase()} />
          <InfoCard title="Machine" value={operation.running ? 'RUNNING' : 'STOPPED'} />
          <InfoCard title="Session" value={operation.paused ? 'PAUSED' : 'ACTIVE / IDLE'} />
          <InfoCard title="Drives" value={`${machine.drives.length} connected`} />
        </section>

        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold">Frequency Drives</h2>
            <p className="text-sm text-muted-foreground">
              Live drive monitoring · 1 second refresh
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {machine.drives.map((drive) => (
              <DriveCard key={drive.id} drive={drive} />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function InfoCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-xl border bg-card p-5">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="mt-2 text-xl font-semibold">{value}</p>
    </div>
  );
}
