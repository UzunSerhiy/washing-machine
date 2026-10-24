export type AutoStatus = 'IDLE' | 'PREPARED' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAULT';

export interface AutoSession {
  status: AutoStatus;
  stage: string | null;
  material_profile_id: number | null;
  speed_percent: number | null;
  running: boolean;
  paused: boolean;
  position_turns: number | null;
  phase: string | null;
  completed: boolean;
}

export type AutoCommand = 'prepare' | 'start' | 'pause' | 'resume' | 'stop';
