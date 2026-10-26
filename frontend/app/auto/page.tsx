"use client";

import { Point0Dialog } from "@/components/machine/point0-dialog";

import { useState } from "react";
import axios from "axios";

import {
  useAutoSession,
  useAutoCommand,
  useSelectAutoMaterial,
} from "@/hooks/use-auto";

import type { AutoCommand } from "@/types/auto";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMaterialProfiles } from "@/hooks/use-material-profiles";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    return error.message;
  }

  return error instanceof Error ? error.message : "Unknown error";
}

export default function AutoPage() {
  const [materialId, setMaterialId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: session, isLoading, isError } = useAutoSession();

  const {
    data: materials = [],
    isLoading: materialsLoading,
    isError: materialsError,
  } = useMaterialProfiles();

  const command = useAutoCommand();
  const selectMaterial = useSelectAutoMaterial();

  const busy = command.isPending || selectMaterial.isPending;
  const status = session?.status ?? "IDLE";

  async function handleCommand(action: AutoCommand) {
    setError(null);

    try {
      await command.mutateAsync(action);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleSelectMaterial() {
    setError(null);

    const id = Number(materialId);

    if (!Number.isInteger(id) || id <= 0) {
      setError("Enter a valid material ID");
      return;
    }

    try {
      await selectMaterial.mutateAsync(id);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  if (isLoading) {
    return <div className="p-6">Loading AUTO session...</div>;
  }

  if (isError || !session) {
    return (
      <div className="p-6 text-red-500">Cannot connect to AUTO session</div>
    );
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="mb-4">
        <Point0Dialog />
      </div>
      <div>
        <h1 className="text-3xl font-bold">Automatic Control</h1>
        <p className="text-muted-foreground">Winding machine · AUTO mode</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Material</CardTitle>
        </CardHeader>

        <CardContent className="flex flex-wrap items-center gap-3">
          {materialsError && (
            <p className="text-sm text-red-500">Failed to load materials</p>
          )}
          <Select
            value={materialId}
            onValueChange={(value) => setMaterialId(value ?? "")}
            disabled={busy || status !== "IDLE" || materialsLoading}
          >
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Select material" />
            </SelectTrigger>

            <SelectContent>
              {materials.map((material) => (
                <SelectItem key={material.id} value={String(material.id)}>
                  {material.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>{" "}
          <Button
            onClick={handleSelectMaterial}
            disabled={
              busy ||
              status !== "IDLE" ||
              !materialId ||
              materialsLoading ||
              materialsError
            }
          >
            Select Material
          </Button>
          <span className="text-sm text-muted-foreground">
            Selected: {session.material_profile_id ?? "None"}
          </span>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>AUTO Status</CardTitle>
        </CardHeader>

        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-sm text-muted-foreground">State</p>
            <p className="text-2xl font-semibold">{status}</p>
          </div>

          <div>
            <p className="text-sm text-muted-foreground">Stage</p>
            <p className="text-xl">{session.stage ?? "—"}</p>
          </div>

          <div>
            <p className="text-sm text-muted-foreground">Speed</p>
            <p className="text-xl">
              {session.speed_percent === null
                ? "—"
                : `${session.speed_percent}%`}
            </p>
          </div>

          <div>
            <p className="text-sm text-muted-foreground">Phase</p>
            <p className="text-xl">{session.phase ?? "—"}</p>
          </div>

          <div>
            <p className="text-sm text-muted-foreground">Roller position</p>
            <p className="text-3xl font-mono">
              {session.position_turns === null
                ? "—"
                : session.position_turns.toFixed(3)}
            </p>
            <p className="text-xs text-muted-foreground">turns</p>
          </div>

          <div>
            <p className="text-sm text-muted-foreground">Completed</p>
            <p className="text-xl">{session.completed ? "Yes" : "No"}</p>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Controls</CardTitle>
        </CardHeader>

        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              disabled={busy || status !== "IDLE"}
              onClick={() => handleCommand("prepare")}
            >
              Prepare
            </Button>

            <Button
              disabled={busy || status !== "PREPARED"}
              onClick={() => handleCommand("start")}
            >
              Start
            </Button>

            <Button
              disabled={busy || status !== "RUNNING"}
              onClick={() => handleCommand("pause")}
            >
              Pause
            </Button>

            <Button
              disabled={busy || status !== "PAUSED"}
              onClick={() => handleCommand("resume")}
            >
              Resume
            </Button>

            <Button
              variant="destructive"
              disabled={busy || status === "IDLE"}
              onClick={() => handleCommand("stop")}
            >
              Stop
            </Button>
          </div>
        </CardContent>
      </Card>
      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600"
        >
          {error}
        </div>
      )}
    </main>
  );
}
