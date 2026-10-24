import { Activity, AlertTriangle, Gauge } from 'lucide-react';
import type { MachineDrive } from '@/types/machine';

interface DriveCardProps {
  drive: MachineDrive;
}

export function DriveCard({ drive }: DriveCardProps) {
  const hasFault = drive.fault !== 0;

  return (
    <div className="rounded-xl border bg-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">{drive.name}</h3>
          <p className="text-sm text-muted-foreground">
            {drive.type} · RS485 #{drive.address}
          </p>
        </div>

        {hasFault ? (
          <AlertTriangle className="text-red-500" />
        ) : (
          <Activity className="text-emerald-500" />
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-bold tabular-nums">{drive.frequency_hz.toFixed(1)}</span>
        <span className="text-muted-foreground">Hz</span>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 text-muted-foreground">
          <Gauge size={16} />
          Status: {drive.status}
        </span>

        <span className={hasFault ? 'text-red-500' : 'text-emerald-500'}>
          {hasFault ? `Fault ${drive.fault}` : 'No fault'}
        </span>
      </div>
    </div>
  );
}
