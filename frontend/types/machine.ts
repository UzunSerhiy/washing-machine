export type MachineMode = 'manual' | 'auto' | 'calibration';

export type DriveType = 'ROLLER' | 'BRUSH';

export interface MachineDrive {
  id: number;
  name: string;
  address: number;
  type: DriveType;
  position: string | null;
  enabled: boolean;
  status: number;
  frequency_hz: number;
  fault: number;
}

export interface Machine {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  drives: MachineDrive[];
}

export interface MachineOperation {
  mode: MachineMode;
  auto_stage: string | null;
  material_profile_id: number | null;
  roller_speed_percent: number | null;
  brush_speed_percent: number | null;
  roller_running: boolean;
  brush_running: boolean;
  running: boolean;
  paused: boolean;
}
