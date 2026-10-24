from typing import Protocol

from app.services.machine.drive_status import (
    DriveStatus,
    MachineDrivesStatus,
)


class DiagnosticsProvider(Protocol):
    def get_drives_status(self) -> MachineDrivesStatus: ...


class DriveDiagnosticsService:
    def __init__(
        self,
        diagnostics_provider: DiagnosticsProvider | None = None,
    ) -> None:
        self.diagnostics_provider = diagnostics_provider

    def require_drives_ready(self) -> None:
        if self.diagnostics_provider is None:
            raise RuntimeError(
                "Cannot reset fault: diagnostics provider is not configured"
            )

        get_status = getattr(
            self.diagnostics_provider,
            "get_drives_status",
            None,
        )

        if callable(get_status):
            try:
                status = get_status()
            except Exception as exc:
                raise RuntimeError(
                    "Cannot reset fault: diagnostics provider check failed"
                ) from exc

            if not isinstance(status, MachineDrivesStatus):
                raise RuntimeError("Cannot reset fault: invalid drive diagnostics")

            self._validate_drive("roller", status.roller)
            self._validate_drive("brushes", status.brushes)
            return

        # Временная совместимость со старым интерфейсом.
        legacy_check = getattr(
            self.diagnostics_provider,
            "are_drives_ready",
            None,
        )

        if not callable(legacy_check):
            raise RuntimeError("Cannot reset fault: diagnostics provider check failed")

        try:
            drives_ready = legacy_check()
        except Exception as exc:
            raise RuntimeError(
                "Cannot reset fault: diagnostics provider check failed"
            ) from exc

        if drives_ready is not True:
            raise RuntimeError("Cannot reset fault: drive diagnostics are not ready")

    @staticmethod
    def _validate_drive(name: str, status: DriveStatus) -> None:
        if not isinstance(status, DriveStatus):
            raise RuntimeError(f"Cannot reset fault: {name} invalid diagnostics")

        if not status.connected:
            raise RuntimeError(f"Cannot reset fault: {name} communication unavailable")

        if status.faulted:
            raise RuntimeError(f"Cannot reset fault: {name} drive fault detected")

        if status.running:
            raise RuntimeError(f"Cannot reset fault: {name} drive is running")

        frequency = status.frequency_hz

        if not isinstance(frequency, (int, float)) or isinstance(frequency, bool):
            raise RuntimeError(f"Cannot reset fault: {name} invalid frequency")

        import math

        if not math.isfinite(frequency) or frequency < 0:
            raise RuntimeError(f"Cannot reset fault: {name} invalid frequency")

        if frequency > 0.0:
            raise RuntimeError(
                f"Cannot reset fault: {name} output frequency is not zero"
            )
