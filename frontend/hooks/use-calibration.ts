"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getCalibrationSession,
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

function useCalibrationMutation<T>(
  mutationFn: (variables: T) => Promise<unknown>,
) {
  const queryClient = useQueryClient();

  return useMutation({
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
    (params: { direction: CalibrationJogDirection; frequencyHz: number }) =>
      jogCalibration(params.direction, params.frequencyHz),
  );
}

export function useCalibrationAction() {
  return useCalibrationMutation(calibrationAction);
}

export function useMarkCalibrationPoint() {
  return useCalibrationMutation((point: CalibrationPoint) =>
    markCalibrationPoint(point),
  );
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
