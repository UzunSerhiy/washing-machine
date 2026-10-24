"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getCalibrationSession,
  autoWindCalibration,
  resumeCalibration,
  nextCalibrationStep,
  startCalibration,
  jogCalibration,
  calibrationAction,
  markCalibrationPoint,
  completeCalibration,
  cancelCalibration,
  startCalibrationBrush,
  stopCalibrationBrush,
  getCalibrationHome,
  startCalibrationHome,
  getRollerReference,
  saveCalibrationGeometry,
} from "@/lib/calibration-api";

import type {
  CalibrationPoint,
  CalibrationJogDirection,
} from "@/types/calibration";

const KEY = ["calibration-session"];

export function useCalibrationSession(enabled = true) {
  return useQuery({
    queryKey: KEY,
    queryFn: getCalibrationSession,
    enabled,
    retry: false,
    refetchInterval: 300,
  });
}

function useCalibrationMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();

  return useMutation<TData, Error, TVariables>({
    mutationFn,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: KEY });
      await queryClient.invalidateQueries({ queryKey: ["machine"] });
    },
  });
}

export function useStartCalibration() {
  return useCalibrationMutation(startCalibration);
}

export function useJogCalibration() {
  return useCalibrationMutation(
    (params: {
      direction: CalibrationJogDirection;
      frequencyHz: number;
      brushFrequencyHz?: number;
    }) =>
      jogCalibration(
        params.direction,
        params.frequencyHz,
        params.brushFrequencyHz,
      ),
  );
}

export function useCalibrationAction() {
  return useCalibrationMutation(calibrationAction);
}

export function useMarkCalibrationPoint() {
  return useCalibrationMutation(
    (params: { point: CalibrationPoint; brushFrequencyHz?: number }) =>
      markCalibrationPoint(params.point, params.brushFrequencyHz),
  );
}

export function useNextCalibrationStep() {
  return useCalibrationMutation(nextCalibrationStep);
}

export function useCompleteCalibration() {
  return useCalibrationMutation(completeCalibration);
}

export function useCancelCalibration() {
  return useCalibrationMutation(cancelCalibration);
}

export function useStartCalibrationBrush() {
  return useCalibrationMutation(startCalibrationBrush);
}

export function useStopCalibrationBrush() {
  return useCalibrationMutation(stopCalibrationBrush);
}

export function useCalibrationHome() {
  return useQuery({
    queryKey: ["calibration-home"],
    queryFn: getCalibrationHome,
    retry: false,
    refetchInterval: 300,
  });
}

export function useRollerReference() {
  return useQuery({
    queryKey: ["roller-reference"],
    queryFn: getRollerReference,
    retry: false,
    refetchInterval: 300,
  });
}

export function useStartCalibrationHome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: startCalibrationHome,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["calibration-home"] });
      await queryClient.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useSaveCalibrationGeometry() {
  return useCalibrationMutation(saveCalibrationGeometry);
}

export function useAutoWindCalibration() {
  return useCalibrationMutation(autoWindCalibration);
}
export function useResumeCalibration() {
  return useCalibrationMutation(resumeCalibration);
}
