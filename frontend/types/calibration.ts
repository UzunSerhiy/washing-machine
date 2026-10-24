export interface CalibrationSession {
  active: boolean;
  material_profile_id: number | null;
  stage:
    | "set_zero"
    | "material_start"
    | "material_end"
    | "water_start"
    | "washing_stop"
    | "ready_to_unwind"
    | "rewind_complete"
    | null;

  saved: boolean;
  auto_mode: "unwinding" | "winding" | "paused" | null;
  position_turns: number;
  running: boolean;
  paused: boolean;
  direction: string | null;
  frequency_hz: number | null;

  brush_running: boolean;
  brush_frequency_hz: number | null;

  washing_stop_turns: number | null;
  material_start_turns: number | null;
  material_end_turns: number | null;
  water_start_turns: number | null;
}

export type CalibrationPoint =
  | "washing_stop"
  | "material_start"
  | "material_end"
  | "water_start";

export type CalibrationJogDirection = "forward" | "reverse";

export interface CalibrationCompleteResponse {
  status: string;
  machine_id: number;
  material_profile_id: number;
}


export interface CalibrationHomeStatus {
  available: boolean;
  state: "idle" | "searching" | "completed" | "cancelled" | "error" | null;
  error: string | null;
}

export interface RollerReferenceState {
  connected: boolean;
  triggered: boolean;
  pulses: number;
  sequence: number;
}
