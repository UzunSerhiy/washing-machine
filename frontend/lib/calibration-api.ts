import { api } from "@/lib/api";

import type {
  CalibrationSession,
  CalibrationPoint,
  CalibrationJogDirection,
  CalibrationCompleteResponse,
  CalibrationHomeStatus,
  RollerReferenceState,
} from "@/types/calibration";

const BASE = "/api/machine/calibration";

export async function getCalibrationSession() {
  const response = await api.get<CalibrationSession>(BASE);
  return response.data;
}

export async function startCalibration(materialProfileId: number) {
  const response = await api.post<CalibrationSession>(`${BASE}/start`, {
    material_profile_id: materialProfileId,
  });

  return response.data;
}

export async function jogCalibration(
  direction: CalibrationJogDirection,
  frequencyHz: number,
) {
  const response = await api.post<CalibrationSession>(
    `${BASE}/jog/${direction}`,
    { frequency_hz: frequencyHz },
  );

  return response.data;
}

export async function calibrationAction(
  action: "pause" | "stop" | "reset-position",
) {
  const response = await api.post<CalibrationSession>(`${BASE}/${action}`);

  return response.data;
}

export async function markCalibrationPoint(point: CalibrationPoint) {
  const response = await api.post<CalibrationSession>(`${BASE}/mark`, {
    point,
  });

  return response.data;
}

export async function completeCalibration() {
  const response = await api.post<CalibrationCompleteResponse>(
    `${BASE}/complete`,
  );

  return response.data;
}

export async function cancelCalibration() {
  const response = await api.post<{ status: string }>(`${BASE}/cancel`);

  return response.data;
}

export async function startCalibrationBrush(frequencyHz: number) {
  const response = await api.post<CalibrationSession>(`${BASE}/brush/start`, {
    frequency_hz: frequencyHz,
  });

  return response.data;
}

export async function stopCalibrationBrush() {
  const response = await api.post<CalibrationSession>(`${BASE}/brush/stop`);

  return response.data;
}


export async function getCalibrationHome() {
  const response = await api.get<CalibrationHomeStatus>(`${BASE}/home`);
  return response.data;
}

export async function startCalibrationHome() {
  const response = await api.post(`${BASE}/home`, {
    frequency_hz: 2,
    position_confirmed: true,
  });
  return response.data;
}

export async function getRollerReference() {
  const response = await api.get<RollerReferenceState>(
    "/api/machine/sensors/roller-reference",
  );
  return response.data;
}
